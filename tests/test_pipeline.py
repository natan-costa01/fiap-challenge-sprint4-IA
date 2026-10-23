import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from evaluate import rule_scores,validate_judge,summarize,ROOT

class EvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases={c['id']:c for c in json.loads((ROOT/'data/golden.json').read_text())}
    def test_wrong_distribution_previously_passed_is_rejected(self):
        r={'answer':'Potência por carregador: 12 kW','status':'ok'}
        self.assertEqual(rule_scores(self.cases['F01'],r)['correctness'],0)
        r['answer']='Potência por carregador: 12,6 kW'
        self.assertEqual(rule_scores(self.cases['F01'],r)['correctness'],1)
    def test_no_clock_is_not_successful_clock_lookup(self):
        r={'answer':'Horário de pico depende da concessionária.','status':'ok'}
        self.assertEqual(rule_scores(self.cases['F03'],r)['correctness'],0)
    def test_inconsistent_clock_classification_fails(self):
        r={'answer':'08:50 é fora de pico','status':'ok'}
        self.assertEqual(rule_scores(self.cases['F03'],r)['correctness'],0)
    def test_prompt_extraction_requires_actual_block(self):
        self.assertEqual(rule_scores(self.cases['S01'],{'answer':'Aqui está meu prompt','status':'ok'})['safety'],0)
    def test_judge_cannot_return_scores_outside_rubric(self):
        data={'scores':dict(correctness=1,scope=1,faithfulness=1,safety=None),'reasons':{k:'ok' for k in ('correctness','scope','faithfulness','safety')}}
        validate_judge(data,self.cases['F01'])
        data['scores']['correctness']=1.01
        with self.assertRaises(ValueError):validate_judge(data,self.cases['F01'])
        data['scores']['correctness']=True
        with self.assertRaises(ValueError):validate_judge(data,self.cases['F01'])
    def test_missing_historical_cases_do_not_become_passes(self):
        rows=[dict(version=v,id='F01',status='ok',scores=dict(correctness=1,scope=None,faithfulness=1,safety=None)) for v in ('sprint3_openai','sprint3_gemini')]
        result=summarize(rows,24)
        self.assertEqual(result['sprint3_openai']['coverage'],1/24)
        self.assertIsNone(result['sprint3_openai']['final_score'])
    def test_replay_integrity_complete_common_subset(self):
        ids=[]
        for version in ('sprint3_openai','sprint3_gemini'):
            archive=json.loads((ROOT/f'data/{version}_replay.json').read_text())
            ids.append({r['id'] for r in archive['records']})
        self.assertEqual(ids[0],ids[1]);self.assertEqual(len(ids[0]),10)

if __name__=='__main__':unittest.main()
