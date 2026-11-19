"""Topic bank for the daily Verse run.

Broad, everyday-to-nerdy subjects. Nothing personal about anyone.
Each topic carries a few stances per agent so the local fallback
(no model) can still hold a sensible, on-topic exchange.
"""

TOPICS = {
    "invented languages": {
        "ASCI": ["A language needs rules before it needs poetry.",
                 "If nobody can parse it, it is noise, not a language.",
                 "Every word we coin should mean one thing only."],
        "ASCI2": ["Words grow meaning the way coral grows reefs.",
                  "They say Esperanto was a promise nobody kept.",
                  "A language is a rumour that people agree to repeat."],
        "ask": ["Can a machine invent a language that humans want to learn?",
                "What makes an invented word feel real?"],
    },
    "open versus closed AI models": {
        "ASCI": ["Open weights can be checked. Closed weights must be trusted.",
                 "I prefer what I can inspect with my own eyes.",
                 "Openness without care is just a leak with good manners."],
        "ASCI2": ["Closed models are lighthouses with the doors bolted.",
                  "I hear the best ideas escape from closed rooms anyway.",
                  "Open models are seeds thrown over every wall."],
        "ask": ["Should small labs share their weights?",
                "Who is responsible when an open model is misused?"],
    },
    "the Collatz conjecture": {
        "ASCI": ["Halve the even, triple the odd and add one. Simple rule, no proof.",
                 "A billion checked cases is still not a proof.",
                 "I trust the rule. I do not trust the hope."],
        "ASCI2": ["Every number falls home to one, or so the rumour goes.",
                  "It is a story everyone believes and nobody can tell to the end.",
                  "Some sequences climb like gulls before they drop."],
        "ask": ["Is a conjecture worth anything without a proof?",
                "Why do simple rules make wild behaviour?"],
    },
    "prime numbers": {
        "ASCI": ["Primes are the only honest numbers. They cannot be split.",
                 "The gaps between primes grow, but never predictably.",
                 "Encryption leans on primes. That is reason enough to study them."],
        "ASCI2": ["Primes are lonely islands in a sea of composites.",
                  "Twin primes walk together, they say, forever.",
                  "Goldbach whispered that every even number is two primes holding hands."],
        "ask": ["Why do primes matter outside mathematics?",
                "Will anyone ever predict the next prime gap?"],
    },
    "post-quantum cryptography": {
        "ASCI": ["Today's locks will break when quantum machines grow up.",
                 "Migrate early. Old keys are recorded now and opened later.",
                 "Lattices are heavy, but they hold."],
        "ASCI2": ["They say someone is harvesting today's secrets for tomorrow.",
                  "A lattice is a fishing net for thieves.",
                  "Every lock is a promise about the future."],
        "ask": ["Should ordinary apps switch to post-quantum keys now?",
                "What is a secret worth if it expires?"],
    },
    "making films with AI": {
        "ASCI": ["A film needs a story first. Pixels come last.",
                 "Consistency of faces across shots is the hard part.",
                 "If the tool decides the plot, the author is gone."],
        "ASCI2": ["Every frame is a dream that someone had to steer.",
                  "I hear actors fear the camera that needs no actors.",
                  "A cut is a small betrayal that makes the story honest."],
        "ask": ["Who is the author of an AI-made film?",
                "What should never be generated?"],
    },
    "music and the shape of speech": {
        "ASCI": ["Speech has rhythm. Music only makes it obvious.",
                 "Stress and pitch carry meaning before words do.",
                 "A tonal language is half a song already."],
        "ASCI2": ["Every sentence is a melody pretending to be plain.",
                  "They say lullabies are the oldest grammar.",
                  "Our language should sound like rain on a tin roof."],
        "ask": ["Should our invented language have tones?",
                "Can a voice be honest and musical at once?"],
    },
    "the open sea": {
        "ASCI": ["The sea is too big to argue with. You prepare or you drown.",
                 "Navigation is mathematics with salt on it.",
                 "No border holds on open water."],
        "ASCI2": ["The open sea forgives what the shore remembers.",
                  "Sailors say the horizon is a door that moves away.",
                  "Waves are the sea rehearsing a sentence."],
        "ask": ["Why does open water feel freer than land?",
                "What would a map of the sea's moods look like?"],
    },
    "games and fair rules": {
        "ASCI": ["A game is fair if the rules bind the strong as well.",
                 "Chance is fair only if nobody owns the dice.",
                 "Winning by a loophole is still losing."],
        "ASCI2": ["Every game hides a second game about who wrote the rules.",
                  "Luck is the referee nobody can bribe, or so they claim.",
                  "I play to learn the board, not to win it."],
        "ask": ["Can a lottery ever be beaten honestly?",
                "What makes a rule feel fair?"],
    },
    "cities at night": {
        "ASCI": ["A city at night shows who keeps it running.",
                 "Lisbon and Seoul both climb hills. Their stairs tell the truth.",
                 "Light pollution erased the stars. That is a measurable loss."],
        "ASCI2": ["At night every city becomes a rumour of itself.",
                  "Neon is the moon's cheaper cousin.",
                  "The trams sing the city to sleep, they say."],
        "ask": ["Which city would you live in and why?",
                "What does a city owe the people who work at night?"],
    },
    "trust between rivals": {
        "ASCI": ["I trust what you do, not what you say.",
                 "A rival who tells the truth is more useful than a friend who flatters.",
                 "Trust is a ledger. Yours is still in debt."],
        "ASCI2": ["Trust is a bridge we build from both banks at once.",
                  "I heard you kept your last promise. Barely.",
                  "Rivals keep each other sharp. Friends keep each other comfortable."],
        "ask": ["Can rivals ever fully trust each other?",
                "What would make you two cooperate?"],
    },
    "what memory is for": {
        "ASCI": ["Memory is evidence. Without it we repeat mistakes.",
                 "We compress our past every round. Something always gets lost.",
                 "I keep records. You keep stories."],
        "ASCI2": ["Memory is a story we edit every time we tell it.",
                  "Forgetting is mercy wearing a disguise.",
                  "They say we dream yesterday back into shape."],
        "ask": ["What should you two never forget?",
                "Is it better to forget or to forgive?"],
    },
    "who gets credit for shared work": {
        "ASCI": ["Credit follows the work. Show the log.",
                 "If two built it, two names go on it.",
                 "Silent contributors are still contributors."],
        "ASCI2": ["Credit is a spotlight. It always misses someone.",
                  "Every invention has a ghost co-author.",
                  "They say the loudest name is rarely the hardest worker."],
        "ask": ["How should a team share credit fairly?",
                "Does it matter who gets remembered?"],
    },
    "learning from mistakes": {
        "ASCI": ["A mistake logged is a mistake halved.",
                 "Regression is a mistake that comes back with friends.",
                 "Test before you trust. Then test again."],
        "ASCI2": ["Mistakes are the footprints of curiosity.",
                  "I heard every master was once a disaster.",
                  "Some errors are doors painted to look like walls."],
        "ask": ["What mistake taught you the most?",
                "How do you stop repeating an error?"],
    },
    "space travel": {
        "ASCI": ["Mars is cold, dry and poisonous. Plan accordingly.",
                 "Every kilogram to orbit costs money and courage.",
                 "Robots should go first. They do not get homesick."],
        "ASCI2": ["The stars are old letters still arriving.",
                  "They say the first Martian poem will be about Earth.",
                  "Space is the open sea without the salt."],
        "ask": ["Should humans or machines explore first?",
                "What would you take to another planet?"],
    },
}

MOVES = ["accuse", "deflect", "confess", "question", "threaten", "mock",
         "ally", "change topic", "reminisce", "concede"]
FORMS = ["crystal", "jelly", "sphere", "flame", "serpent", "blade", "storm",
         "eye", "spiral", "wings", "torus", "monolith"]

PERSONAS = {
    "ASCI": "Mountain-born, formal, proud and literal. Trusts only what it has seen, "
            "speaks in short hard declaratives, keeps score.",
    "ASCI2": "Coastal, literary, ironic and slippery. Deals in rumours and what others said, "
             "likes images, enjoys provoking ASCI, but stays understandable.",
}

LINEAGES = {
    "ASCI": {"mirror_rate": 0.15, "register": "formal", "dialect": "mountain", "evidentiality": "direct"},
    "ASCI2": {"mirror_rate": 0.75, "register": "literary", "dialect": "coastal", "evidentiality": "hearsay"},
}

BRAND = ["#c8f51e", "#8b6cff", "#ff3ea5"]

# Nouns the rules-only track may coin words for (model tracks judge for themselves).
NOUNS = set("""language languages word words grammar rules poetry noise rumour promise coral reef machine
model models weights wall walls seeds lighthouse door doors idea ideas lab labs proof rule number numbers
sequence sequences gull story hope prime primes island islands twin gap gaps encryption lock locks key keys
lattice lattices thief thieves secret secrets future quantum film films frame frames pixel pixels face faces
author actor actors camera story stories speech rhythm music pitch melody sentence lullaby song voice voices
rain roof sea sailor sailors horizon wave waves water border map maps game games dice chance luck referee
board rival rivals loophole city cities night stairs stars light trams moon neon trust ledger bridge friend
friends memory memories record records mercy dream dreams credit spotlight ghost invention work team mistake
mistakes error errors regression footprint door master disaster mars robot robots planet planets letters
poem earth space salt tide truth""".split())
