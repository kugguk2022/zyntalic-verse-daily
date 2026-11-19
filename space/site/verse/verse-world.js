"use strict";

const VerseWorld = (() => {
  const clamp = value => Math.max(0, Math.min(1, value));
  const ease = (current, target, amount) => current + (target - current) * amount;
  const actions = {
    open: {
      label: "opens the floodgate", topic: "the rising water", move: "question",
      forms: ["blade", "serpent"],
      allowed: w => w.gate < .86,
      change: w => { w.gate += .54; },
      lines: [
        ["I lift the gate. Watch what your silence has been holding back.", "Let the river show us what the ledger concealed."],
        ["There. A door the water knows how to use.", "Open mouths make better rivers than clenched teeth."],
      ],
    },
    close: {
      label: "closes the floodgate", topic: "pressure behind the gate", move: "deflect",
      forms: ["monolith", "torus"],
      allowed: w => w.gate > .12,
      change: w => { w.gate -= .64; },
      lines: [
        ["I shut the gate. Count the seconds before the river answers.", "Water can wait. The people below cannot."],
        ["I draw the passage shut. Listen to the water pressing back.", "We have bought a quiet moment. Please spend it wisely."],
      ],
    },
    brace: {
      label: "raises stone braces", topic: "what the bank can hold", move: "ally",
      forms: ["crystal", "wings"],
      allowed: w => w.support < .84,
      change: w => { w.support += .39; },
      lines: [
        ["Hold the footing. I can brace this wall from my side.", "Put your weight on the sound stone. I will hold the rest."],
        ["Lean here. I can weave a brace from the pieces that held.", "Give me your strongest stone. I will find where it fits."],
      ],
    },
    break: {
      label: "fractures the crossing", topic: "a way across", move: "accuse",
      forms: ["flame", "storm"],
      allowed: w => w.damage < .75 && (w.pressure > .48 || w.gate > .48),
      change: w => { w.damage += .61 - w.support * .23; w.support -= .2; },
      lines: [
        ["The span has cracked. Find another way across.", "I heard the stone give. Tell me who is still on the far bank."],
        ["The crossing breaks under us. Can you hear the stones sink?", "There goes our bridge. Which of us will ask for help first?"],
      ],
    },
    repair: {
      label: "knits the crossing together", topic: "rebuilding the crossing", move: "ally",
      forms: ["monolith", "spiral"],
      allowed: w => w.damage > .15,
      change: w => { w.damage -= .42; w.support += .16; },
      lines: [
        ["Pass me the fallen stones. I can rebuild the center span.", "One course at a time. I will show you where the keystone goes."],
        ["We could weave a bridge from the pieces we still have.", "Leave a gap for the current. This time let the water through."],
      ],
    },
    signal: {
      label: "sends a signal downriver", topic: "who heard the signal", move: "question",
      forms: ["eye", "wings"],
      allowed: w => w.signal < .53,
      change: w => { w.signal += .83; },
      lines: [
        ["I light the tower. Someone across the water must see us.", "Three pulses. If they see us, ask them to send two back."],
        ["Send a light through the mist. Let us see who answers.", "Look up. I have left a thread of light over the far bank."],
      ],
    },
  };
  const keys = Object.keys(actions);

  function create() {
    return {
      exchange: 0, topic: "the floodgate", gate: .04, water: .1, pressure: .58,
      damage: 0, support: .13, signal: 0, lastAction: null,
    };
  }

  function scene(w) {
    if (w.damage > .46) return "Broken crossing";
    if (w.signal > .45) return "Signal vault";
    if (w.water > .43) return "Flooded channel";
    if (w.support > .49) return "Reinforced banks";
    return "Floodgate";
  }

  function available(w) { return keys.filter(key => actions[key].allowed(w)); }

  function step(previous, turn) {
    const w = { ...previous, exchange: previous.exchange + 1 };
    const key = available(previous).includes(turn.action) ? turn.action : null;
    if (key) {
      actions[key].change(w);
      w.lastAction = { action: key, by: turn.who, exchange: w.exchange };
    }
    w.topic = turn.topic || (key && actions[key].topic) || w.topic;
    for (const state of ["gate", "damage", "support", "signal"]) w[state] = clamp(w[state]);
    if (key !== "signal") w.signal = Math.max(0, w.signal - .15);
    w.water = ease(w.water, clamp(.12 + w.gate * .75 + w.damage * .31), .51);
    w.pressure = ease(w.pressure, clamp(.8 - w.gate * .58 + w.damage * .18 - w.support * .19), .36);
    return w;
  }

  function context(w) {
    const fraction = n => Math.round(n * 100) + "%";
    const crossing = w.damage > .46 || w.water > .63 ? "impassable" : w.water > .39 ? "slippery" : "passable";
    return [
      scene(w) + ". Current subject: " + w.topic + ".",
      "Gate " + fraction(w.gate) + " open. Water " + fraction(w.water) + ". Pressure " + fraction(w.pressure) + ".",
      "Crossing is " + crossing + ". Damage " + fraction(w.damage) + ". Stone bracing " + fraction(w.support) + ".",
      w.lastAction ? w.lastAction.by + " " + actions[w.lastAction.action].label + " at exchange " + w.lastAction.exchange + "." : "",
    ].filter(Boolean).join(" ");
  }

  function localTurn(w, who, visitor, rng) {
    const choices = available(w);
    const player = who === "ASCI" ? 0 : 1;
    const input = visitor?.text.toLowerCase() || "";
    const suggestion = /\b(open|release|flood)\b/.test(input) ? "open"
      : /\b(close|shut)\b/.test(input) ? "close"
      : /\b(repair|rebuild|mend)\b/.test(input) ? "repair"
      : /\b(brace|support|reinforce)\b/.test(input) ? "brace"
      : /\b(signal|light|beacon)\b/.test(input) ? "signal" : null;
    const weights = {
      open: w.gate < .25 ? 2.5 + player : .7,
      close: w.water > .42 ? 4 + 1.7 * (1 - player) : .3,
      brace: 1.25 + (1 - player) + w.pressure,
      break: 1.1 + w.gate * 2 + player,
      repair: .7 + w.damage * 7,
      signal: .85 + player + (w.damage > .42 ? 2 : 0),
    };
    const prior = w.lastAction?.action;
    const scores = choices.map(key => weights[key] * (prior === key ? .12 : 1));
    let remaining = rng() * scores.reduce((a, b) => a + b, 0);
    const action = suggestion && choices.includes(suggestion) ? suggestion : choices.find((_, index) => {
      remaining -= scores[index];
      return remaining < 0;
    }) || choices[0];
    const a = actions[action];
    const line = a.lines[player][Math.floor(rng() * a.lines[player].length)];
    return {
      action, line, topic: a.topic, move: a.move,
      intensity: clamp(.18 + w.pressure * .38 + (action === "break" ? .35 : 0)),
      to: visitor ? "VISITOR" : player ? "ASCI" : "ASCI2",
      form: a.forms[player],
    };
  }

  return { actions, create, scene, available, step, context, localTurn };
})();

if (typeof module !== "undefined" && module.exports) module.exports = VerseWorld;

function createVerseTerrain() {
  const lerp = (a, b, k) => a + (b - a) * k;
  const initial = VerseWorld.create();
  const visual = { ...initial };
  const fields = ["gate", "water", "pressure", "damage", "support", "signal"];
  const seed = n => {
    const value = Math.sin(n * 91.375 + 3.19) * 19498.334;
    return value - Math.floor(value);
  };

  function draw(ctx, width, height, world, palette, time, dt, reducedMotion, voiceLevel) {
    const t = reducedMotion ? 0 : time;
    const follow = reducedMotion ? 1 : 1 - Math.exp(-dt * 2.5);
    for (const field of fields) visual[field] = lerp(visual[field], world[field], follow);
    const { gate, water, pressure, damage, support, signal } = visual;
    const daylight = palette[2];
    const motion = reducedMotion ? 0 : Math.min(1, Math.max(0, voiceLevel));
    const horizon = height * (.48 - water * .052);
    const ridge = height * (.1 + support * .14);
    const mid = width * .5;
    const widthScale = Math.min(width, height * 1.35);
    const split = (u, approach) => Math.sin(u * 13 + t * .6) * pressure * 15 * approach;
    const reach = z => .042 + z * z * .42;

    function point(side, z, bank = 0) {
      const u = z * z;
      return [mid + side * width * (reach(z) + bank * u) + split(z, u),
        horizon + u * height * (.48 - water * .08)];
    }

    ctx.save();
    const sky = ctx.createRadialGradient(mid, horizon, 0, mid, horizon, Math.max(width, height) * .6);
    sky.addColorStop(0, daylight + "25");
    sky.addColorStop(.24, palette[1] + "13");
    sky.addColorStop(1, "#050607");
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, width, height);

    // The river retains its bed while the water and the banks change shape.
    ctx.beginPath();
    for (const side of [-1, 1]) {
      for (let i = 0; i <= 24; i++) {
        const z = side < 0 ? i / 24 : 1 - i / 24;
        const p = point(side, z, water * .09);
        if (side < 0 && i === 0) ctx.moveTo(...p);
        else ctx.lineTo(...p);
      }
    }
    ctx.closePath();
    const river = ctx.createLinearGradient(0, horizon, 0, height);
    river.addColorStop(0, daylight + "70");
    river.addColorStop(.22, palette[0] + "3a");
    river.addColorStop(1, "#06090f");
    ctx.fillStyle = river;
    ctx.globalAlpha = .46 + water * .49;
    ctx.fill();
    ctx.globalAlpha = 1;

    // The same banks raise, shear, and lose blocks as the crossing takes load.
    for (const side of [-1, 1]) {
      for (let i = 0; i < 23; i++) {
        const z = i / 23;
        const u = seed(23 * side + i);
        const near = point(side, z, .06);
        const next = point(side, (i + 1) / 23, .06);
        const crumble = damage * (u > .44 ? 1 : .24);
        const lifted = (z * .75 + .19) * ridge * (.38 + u * 1.25);
        const shear = side * (crumble * widthScale * .075 + support * z * widthScale * .034);
        const roof = near[1] - lifted * (1 - crumble * .78);
        const outside = near[0] + side * width * (.022 + z * .16);
        const wall = ctx.createLinearGradient(0, roof, 0, near[1] + 1);
        wall.addColorStop(0, palette[1] + (i % 3 ? "43" : "60"));
        wall.addColorStop(1, "#08090c");
        ctx.beginPath();
        ctx.moveTo(...near);
        ctx.lineTo(near[0] + shear, roof);
        ctx.lineTo(outside + shear, roof + lifted * .26);
        ctx.lineTo(outside + (next[0] - near[0]), next[1]);
        ctx.closePath();
        ctx.fillStyle = wall;
        ctx.fill();
        ctx.strokeStyle = palette[0] + (i % 4 ? "21" : "63");
        ctx.lineWidth = 1;
        ctx.stroke();
        if (u > .48 && i > 7) {
          ctx.beginPath();
          ctx.moveTo(near[0] + shear, roof + lifted * .07);
          ctx.lineTo(outside + shear, roof + lifted * .3);
          ctx.lineTo(outside + (next[0] - near[0]) * .8, next[1]);
          ctx.strokeStyle = "#131820";
          ctx.stroke();
        }
        if (crumble > .24) {
          for (let chip = 0; chip < 5; chip++) {
            const v = seed(i * 17 + chip);
            const x = near[0] + shear * v + side * widthScale * .025 * Math.sin(v * 19 + t * .6);
            const y = lerp(roof, near[1], v) + 14 * Math.sin(t * .75 + v * 12);
            const size = 1 + v * crumble * 3;
            ctx.fillStyle = daylight + "63";
            ctx.fillRect(x, y, size, size);
          }
        }
      }
    }

    // The current grows into the foreground. Layered ribbons leave a wake.
    for (let lane = -7; lane <= 7; lane++) {
      const s = lane / 8;
      for (let trail = 2; trail >= 0; trail--) {
        if (reducedMotion && trail) continue;
        ctx.beginPath();
        for (let j = 0; j <= 29; j++) {
          const z = j / 29;
          const u = z * z;
          const wake = Math.sin(z * 16 - (t - trail * .13) * (1 + water) + lane * .7);
          const x = mid + s * reach(z) * width * (.54 + water * .86) + wake * u * (10 + 42 * water);
          const y = horizon + u * height * .55 + wake * (2 + water * 10) * u;
          if (j === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = palette[0] + (trail ? "23" : lane % 3 ? "70" : "bd");
        ctx.lineWidth = trail ? 1.4 + trail * .8 : .8 + water * 1.3;
        ctx.globalAlpha = .16 + water * .63;
        ctx.stroke();
      }
    }
    for (let row = 0; row < 26; row++) {
      const z = (.07 + ((row / 26 + t * (.08 + water * .1)) % 1) * .9);
      const [left, y] = point(-1, z, -.13);
      const [right] = point(1, z, -.13);
      const u = seed(row + 2);
      const span = right - left;
      const lo = left + span * u * .68;
      const hi = Math.min(right, lo + span * (.17 + water * .22));
      const crest = 2 + water * z * 7;
      ctx.beginPath();
      ctx.moveTo(lo, y);
      ctx.bezierCurveTo(lo + (hi - lo) * .3, y - crest, hi - (hi - lo) * .25, y + crest, hi, y);
      ctx.globalAlpha = (.11 + water * .54) * Math.sin(z * Math.PI);
      ctx.lineWidth = .4 + z * 1.4;
      ctx.strokeStyle = row % 6 === 0 ? daylight : palette[0];
      ctx.stroke();
    }

    // The central span keeps its silhouette through the morph.
    const spanWidth = widthScale * .225;
    const spanY = horizon + height * .065;
    const crest = spanY - height * (.13 + support * .034 + gate * .042);
    for (let i = 0; i < 24; i++) {
      const u = i / 23;
      const v = seed(i + 10);
      const wave = Math.sin(u * Math.PI);
      const dislodge = damage * wave * (v > .35 ? .5 + v : -.13);
      const x = mid + (u - .5) * spanWidth * 2 + (u - .5) * spanWidth * dislodge * .7;
      const y = lerp(spanY, crest, wave) + height * (dislodge * .115 - gate * wave * .039);
      const thickness = Math.max(2, spanWidth * (.1 - damage * .034));
      ctx.globalAlpha = .82;
      ctx.fillStyle = palette[1] + "8c";
      ctx.fillRect(x - thickness / 2, y, thickness + 1, thickness * (.48 + support * .47));
      ctx.fillStyle = daylight + "ac";
      ctx.fillRect(x - thickness / 2, y, thickness + 1, 1.3);
    }

    if (signal > .02) {
      for (let strand = 0; strand < 9; strand++) {
        const offset = strand - 4;
        ctx.beginPath();
        ctx.moveTo(mid - spanWidth * 1.5, spanY - offset * 3);
        ctx.bezierCurveTo(mid - spanWidth * .2, crest - height * (.22 + signal * .13) + offset * 8,
          mid + spanWidth * .42, crest + Math.sin(t * 2 + offset) * 14,
          mid + spanWidth * 1.65, spanY + offset * 3);
        ctx.globalAlpha = signal * (.36 + (strand % 3) * .17);
        ctx.lineWidth = strand % 3 ? 1 : 2;
        ctx.strokeStyle = daylight;
        ctx.stroke();
      }
    }

    const mist = ctx.createLinearGradient(0, horizon - 24, 0, horizon + height * .16);
    mist.addColorStop(0, palette[0] + "00");
    mist.addColorStop(.42, palette[0] + "49");
    mist.addColorStop(1, palette[0] + "00");
    ctx.globalAlpha = .22 + water * .2 + motion * .15;
    ctx.fillStyle = mist;
    ctx.fillRect(0, horizon - 24, width, height * .17 + 24);
    ctx.restore();
  }

  return { draw };
}

if (typeof module !== "undefined" && module.exports) module.exports.createTerrain = createVerseTerrain;
