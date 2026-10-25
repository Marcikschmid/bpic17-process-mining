"""Exercise the native PM4Py Genetic Miner adapter on small, real inputs."""
import unittest
import pandas as pd
import networkx as nx
from src.genetic_miner import discover_genetic

class GeneticMinerTests(unittest.TestCase):
    def frame(self):
        rows=[('c1','A'),('c1','B'),('c1','C'),('c2','A'),('c2','C'),('c2','B')]
        return pd.DataFrame({'case:concept:name':[r[0] for r in rows],
            'concept:name':[r[1] for r in rows],
            'time:timestamp':pd.date_range('2020-01-01',periods=len(rows),freq='s',tz='UTC')})

    def test_native_output_input_preservation_and_seeded_isomorphism(self):
        frame=self.frame();before=frame.copy(deep=True)
        models=[discover_genetic(frame,seed=123,population_size=4,generations=1,elitism_min_sample=2) for _ in range(2)]
        pd.testing.assert_frame_equal(frame,before)
        graphs=[]
        for net,initial,final in models:
            self.assertEqual({t.label for t in net.transitions if t.label is not None},{'A','B','C'})
            graph=nx.DiGraph()
            for p in net.places:graph.add_node(p,kind='place',label=None,initial=initial.get(p,0),final=final.get(p,0))
            for t in net.transitions:graph.add_node(t,kind='transition',label=t.label,initial=0,final=0)
            for arc in net.arcs:graph.add_edge(arc.source,arc.target,weight=arc.weight)
            graphs.append(graph)
        self.assertTrue(nx.is_isomorphic(*graphs,node_match=lambda a,b:a==b,edge_match=lambda a,b:a==b))

    def test_duplicate_silent_names_export_without_losing_connections(self):
        import tempfile
        import xml.etree.ElementTree as ET
        from pathlib import Path
        import pm4py
        from pm4py.objects.petri_net.obj import PetriNet,Marking
        from pm4py.objects.petri_net.utils.petri_utils import add_arc_from_to
        from scripts.discover_models import export_model,ROOT
        from src.runtime import configure_runtime
        from src.replay_coverage import ExactReplay
        configure_runtime()
        net=PetriNet('duplicate_names')
        places=[PetriNet.Place(f'p{i}') for i in range(3)]
        silent=[PetriNet.Transition('',None) for _ in range(2)]
        net.places.update(places);net.transitions.update(silent)
        for i,t in enumerate(silent):
            add_arc_from_to(places[i],t,net);add_arc_from_to(t,places[i+1],net)
        initial=Marking({places[0]:1});final=Marking({places[2]:1})
        with tempfile.TemporaryDirectory(dir=ROOT/'tmp') as folder:
            export_model('regression',(net,initial,final),Path(folder))
            path=Path(folder)/'models/regression.pnml'
            ids=[element.attrib['id'] for element in ET.parse(path).iter()
                 if element.tag in ('place','transition') and 'id' in element.attrib]
            self.assertEqual(len(ids),len(set(ids)))
            restored=pm4py.read_pnml(str(path))
            coverage=ExactReplay(*restored).evaluate([[]])[0]
            self.assertEqual(coverage['fitting_cases'],1)
            self.assertTrue(coverage['sound'])
        self.assertEqual([t.name for t in silent],['',''])

    def test_invalid_budget_and_tournament_rejected_before_native_search(self):
        for parameters in ({'population_size':1},{'generations':0},{'population_size':3,'elitism_min_sample':3},{'mutation_rate':1.1}):
            with self.subTest(parameters=parameters),self.assertRaises(ValueError):
                discover_genetic(self.frame(),**parameters)

if __name__=='__main__':unittest.main()
