import unittest,tempfile
from pathlib import Path
import numpy as np
from src.runtime import configure_runtime
configure_runtime()
import pm4py
from pm4py.objects.process_tree.utils.generic import parse
from pm4py.objects.log.obj import Trace,Event
from pm4py.algo.conformance.alignments.petri_net import algorithm as ali
from src.finite_alignment import FiniteAligner
from src.decision_mining import observations,encode_features,tree_rules,predict_rules,bpmn_net,guarded_accepts,NS
from src.replay_coverage import ExactReplay


class DecisionTests(unittest.TestCase):
    def test_alignment_costs_match_reference_with_loops_parallelism_and_deviations(self):
        for expression,traces in [("->('A',X('B',tau),'C')",[['A','C'],['A','X','C'],['C']]),
                ("->(+('A','B'),*('C','D'))",[['B','A','C'],['A','B','D','C'],['A','B','C','D','C']]),
                ("X(->('A','B'),->('A','C'))",[['A','B'],['A','D']])]:
            net,im,fm=pm4py.convert_to_petri_net(parse(expression));machine=FiniteAligner(net,im,fm)
            for sequence in traces:
                with self.subTest(expression=expression,sequence=sequence):
                    result=machine.align(sequence);self.assertTrue(machine.verify(sequence,result))
                    reference=ali.apply_trace(Trace([Event({'concept:name':a}) for a in sequence]),net,im,fm)
                    self.assertEqual(result['cost'],reference['cost'])

    def test_state_limit_is_a_failure_not_an_approximation(self):
        with self.assertRaises(ValueError):FiniteAligner(*pm4py.convert_to_petri_net(parse("->('A','B')")),max_states=1)

    def test_future_outcome_and_log_only_moves_do_not_update_inputs(self):
        events=[{'CreditScore':400,'Accepted':True},{'CreditScore':999},{'CreditScore':700}]
        alignment={'moves':[{'kind':'tau','transition':'choice','event_index':None},
            {'kind':'sync','transition':'A','event_index':0},
            {'kind':'log','transition':None,'event_index':1},
            {'kind':'tau','transition':'choice','event_index':None},
            {'kind':'sync','transition':'B','event_index':2},
            {'kind':'tau','transition':'choice','event_index':None}]}
        rows=observations(events,{'RequestedAmount':1000,'concept:name':'secret'},alignment,{'choice':('D01','flow')})
        self.assertNotIn('event_CreditScore',rows[0]['features'])
        self.assertEqual(rows[1]['features']['event_CreditScore'],400)
        self.assertEqual(rows[2]['features']['event_CreditScore'],700)
        self.assertFalse(any('Accepted' in k or 'secret' in str(v) for r in rows for k,v in r['features'].items()))

    def test_exported_rules_partition_missing_categorical_and_numeric_inputs(self):
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.tree import DecisionTreeClassifier
        rows=[{'case_LoanGoal':'Car','event_CreditScore':300},{'case_LoanGoal':'Car','event_CreditScore':800},
              {'case_LoanGoal':'Home'},{'case_LoanGoal':'Home','event_CreditScore':800}]
        vector=DictVectorizer(sparse=False);X=vector.fit_transform([encode_features(r) for r in rows]);y=['A','B','A','B']
        clf=DecisionTreeClassifier(random_state=1).fit(X,y);leaves=tree_rules(clf,vector.get_feature_names_out())
        for row in rows+[{'case_LoanGoal':'NEW'},{'case_LoanGoal':'NEW','event_CreditScore':900}]:
            encoded=encode_features(row);cast={k:float(np.float32(v)) if isinstance(v,(float,int)) else v for k,v in encoded.items()}
            self.assertEqual(predict_rules(leaves,cast),clf.predict(vector.transform([encoded]))[0])

    def test_bpmn_flow_semantics_preserve_language_and_map_each_split_branch(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.bpmn';tree=parse("->('A',X('B',tau),+('C','D'),*('E','F'))")
            pm4py.write_bpmn(pm4py.convert_to_bpmn(tree),str(path))
            net,im,fm,gateways,choices=bpmn_net(path)
            source=ExactReplay(*pm4py.convert_to_petri_net(tree));target=ExactReplay(net,im,fm)
            self.assertTrue(source.language_equivalent(target)['equivalent'])
            splits=[g for g in gateways if g['kind']=='split']
            self.assertTrue(splits)
            for gateway in splits:
                mapped={flow for key,flow in choices.values() if key==gateway['id']}
                self.assertEqual(mapped,set(gateway['outgoing']))

    def test_guarded_replay_rejects_wrong_branch_and_does_not_look_ahead(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.bpmn';tree=parse("X('A','B')")
            pm4py.write_bpmn(pm4py.convert_to_bpmn(tree),str(path))
            net,im,fm,gateways,choices=bpmn_net(path);aligner=FiniteAligner(net,im,fm)
            g=next(g for g in gateways if g['kind']=='split');root=ET.parse(path).getroot()
            nodes={e.attrib.get('id'):e for e in root.find('b:process',NS)}
            flow_a=next(fid for fid in g['outgoing'] if nodes[nodes[fid].attrib['targetRef']].attrib.get('name')=='A')
            flow_b=next(fid for fid in g['outgoing'] if fid!=flow_a)
            leaves=[{'class':flow_a,'predicates':[{'feature':'event_CreditScore','op':'<=','threshold':500}]},
                    {'class':flow_b,'predicates':[{'feature':'event_CreditScore','op':'>','threshold':500}]}]
            models={g['id']:{'leaves':leaves}}
            # Score is only written by the task itself: before XOR it is missing (-1).
            self.assertTrue(guarded_accepts(aligner,[{'concept:name':'A','CreditScore':900}],{},choices,models))
            self.assertFalse(guarded_accepts(aligner,[{'concept:name':'B','CreditScore':900}],{},choices,models))

if __name__=='__main__':unittest.main()
