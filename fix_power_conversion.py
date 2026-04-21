import json
from src.tools.trl_inferencer import TRLInferencer

with open('data/scored/power_conversion_scored.json') as f:
    data = json.load(f)

inferencer = TRLInferencer()
result = inferencer.estimate_trl(data['name'], data['scored_documents'])

with open('data/trl/power_conversion_trl.json', 'w') as f:
    json.dump(result, f, indent=2)

print('TRL:', result['trl_range'])
print('Confidence:', result['confidence'])
print('Summary:', result['summary'])