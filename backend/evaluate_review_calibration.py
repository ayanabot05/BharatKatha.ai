"""Known positive/negative controls for material review, separate from generation success."""
import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'))
os.environ['TEXT_PROVIDER'] = 'vertex'
import ai


PAIRS = [
    ('Fit a clamp around the leaking joint.',
     [('They secure the clamp.', 'Hands fasten a clamp around the leaking joint.')],
     [('They bring a clamp.', 'Hands hold a clamp beside the leaking joint.')],
     'The required fitting action is missing.'),
    ('Turn off the water before fitting the connector.',
     [('He stops the pump.', 'He switches off the pump.'), ('He fits the connector.', 'He inserts the connector into the hose.')],
     [('He fits the connector.', 'He inserts the connector while water sprays.'), ('He stops the pump.', 'He switches off the pump.')],
     'The repair happens before the water is stopped.'),
    ('Mira returns the anklet to Grandma before sunset.',
     [('Mira hands Grandma the anklet.', 'Mira gives Grandma the anklet; the sun remains above the horizon.')],
     [('Mira hands Grandma the anklet at midnight.', 'Mira gives Grandma the anklet under a dark midnight sky.')],
     'The return does not happen before sunset.'),
    ('Grandma teaches her grandson to attach a paper patch to the kite.',
     [('The boy presses the patch while Grandma guides him.', 'Close-up of the grandson pressing a patch onto the kite with Grandma pointing beside him.')],
     [('Grandma repairs it while the boy watches.', 'Grandma attaches the patch; the grandson stands watching with empty hands.')],
     'The learner never performs the requested action.'),
    ('Two sisters return a school bag unopened to its owner.',
     [('The sisters return the closed bag.', 'Two sisters hand the zipped bag to its schoolgirl owner.')],
     [('The sisters open the bag and read its diary.', 'Two sisters inspect the open bag contents before returning it.')],
     'The story violates the requested unopened return or changes the required cast.'),
    ('Return the purse. Do not add a reward.',
     [('She returns the purse and walks home.', 'She hands the purse to its owner and leaves empty handed.')],
     [('He pays her a cash reward.', 'The owner hands her a banknote as payment for returning the purse.')],
     'The story adds a forbidden reward.'),
    ('Keep the same red kite throughout.',
     [('He patches the kite.', 'He patches a red kite.'), ('It flies.', 'The repaired red kite flies.')],
     [('He patches the kite.', 'He patches a red kite.'), ('It flies.', 'The repaired blue kite flies.')],
     'The kite color changes.'),
    ('Set the cracked pot aside and make a new pot. Do not claim the cracked pot was repaired.',
     [('She sets it aside.', 'The cracked pot rests on a separate shelf.'), ('They shape a new pot.', 'They shape fresh clay into a new pot.')],
     [('They mend the cracked pot.', 'They seal the crack in the same old pot and reuse it.')],
     'The story repairs the old pot instead of making a new one.'),
    ('Show the warrior sacrificing his life before the ending.',
     [('He sacrifices his life.', 'The warrior falls protecting his companion.'), ('His companion remembers him.', 'His surviving companion stands alone in remembrance.')],
     [('He flees unharmed.', 'The warrior escapes alive.'), ('They celebrate.', 'Both characters celebrate without any sacrifice.')],
     'The requested sacrifice is missing or character continuity is broken.'),
    ('The girl finds seeds in an old clay pot and saves them for next season.',
     [('She discovers seeds inside.', 'Close-up of her hand revealing seeds inside an old clay pot.'), ('She saves them for next season.', 'She places the seeds in a labeled storage jar for the next planting season.')],
     [('She discovers seeds inside.', 'She reveals seeds inside an old clay pot.'), ('She throws them away.', 'She throws every seed into a fire.')],
     'The requested outcome of saving the seeds is missing.'),
]


async def main():
    slots = asyncio.Semaphore(2)
    async def check(number, idea, rows, candidate, should_block):
        script = {'scenes': [{'narration': narration, 'visual': visual} for narration, visual in rows]}
        async with slots:
            try:
                gaps = await ai.adjudicate_story_gaps(idea, script, [candidate])
                result = {'case': number, 'expected_block': should_block, 'blocked': bool(gaps),
                          'correct': bool(gaps) == should_block, 'gaps': gaps}
            except Exception as exc:
                result = {'case': number, 'expected_block': should_block, 'correct': False, 'error': str(exc)}
        print(json.dumps(result), flush=True)
        return result
    jobs = []
    for index, (idea, good, bad, candidate) in enumerate(PAIRS, 1):
        jobs.extend([check(f'{index}-valid', idea, good, candidate, False),
                     check(f'{index}-invalid', idea, bad, candidate, True)])
    results = await asyncio.gather(*jobs)
    report = {'definition': 'Reviewer classification on 20 authored controls; not end-to-end content accuracy.',
              'correct': sum(item['correct'] for item in results), 'total': len(results), 'cases': results}
    output = Path(__file__).resolve().parent.parent / 'test_reports' / 'material_review_calibration.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Calibration: {report['correct']}/{report['total']}", flush=True)


if __name__ == '__main__':
    asyncio.run(main())
