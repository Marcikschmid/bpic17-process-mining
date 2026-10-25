"""Exact shortest complete alignments on a certified finite marking graph.

Costs match PM4Py's standard profile: sync=0, tau=1, visible/log=10000.
No beam, sampling, timeout or token insertion. Equal costs use stable node names.
"""
from collections import deque
from heapq import heappop, heappush


class FiniteAligner:
    def __init__(self, net, initial, final, max_states=50000, constraints=()):
        self.places = sorted(net.places, key=lambda p:p.name)
        index = {p:i for i,p in enumerate(self.places)}
        self.transitions = sorted(net.transitions, key=lambda t:t.name)
        self.pre, self.post = [], []
        for t in self.transitions:
            if any(a.properties or not isinstance(a.weight,int) or a.weight<=0
                   for a in (*t.in_arcs,*t.out_arcs)):
                raise ValueError('Positive integer ordinary arcs required')
            self.pre.append([(index[a.source],a.weight) for a in t.in_arcs])
            self.post.append([(index[a.target],a.weight) for a in t.out_arcs])
        self.start=tuple(initial.get(p,0) for p in self.places)
        end=tuple(final.get(p,0) for p in self.places)
        self.states=[self.start]; numbers={self.start:0}; self.edges=[]
        for state in self.states:
            outgoing=[]
            for k,t in enumerate(self.transitions):
                if not all(state[p]>=w for p,w in self.pre[k]):continue
                target=list(state)
                for p,w in self.pre[k]:target[p]-=w
                for p,w in self.post[k]:target[p]+=w
                target=tuple(target)
                if any(sum(w*target[p] for p,w in weights)>limit for weights,limit in constraints):continue
                if target not in numbers:
                    if len(numbers)>=max_states:raise ValueError('State cap reached; no partial alignment graph accepted')
                    numbers[target]=len(self.states);self.states.append(target)
                outgoing.append((k,numbers[target]))
            self.edges.append(outgoing)
        if end not in numbers:raise ValueError('Final marking is unreachable in alignment graph')
        self.final=numbers[end]
        # Exact model-only completion distances are admissible lower bounds.
        reverse=[[] for _ in self.states]
        for s,edges in enumerate(self.edges):
            for k,t in edges:reverse[t].append((s,1 if self.transitions[k].label is None else 10000))
        self.completion=[float('inf')]*len(self.states);self.completion[self.final]=0
        queue=[(0,self.final)]
        while queue:
            cost,s=heappop(queue)
            if cost!=self.completion[s]:continue
            for previous,w in reverse[s]:
                if cost+w<self.completion[previous]:
                    self.completion[previous]=cost+w;heappush(queue,(cost+w,previous))

    def align(self, sequence, moves=True):
        """Dijkstra on all (consumed-event index, marking) product states."""
        sequence=tuple(sequence);size=len(self.states)
        start=0;goal=len(sequence)*size+self.final
        distances={start:0};parents={} if moves else None;queue=[(0,start)]
        while queue:
            cost,key=heappop(queue)
            if distances[key]!=cost:continue
            if key==goal:
                result={'cost':cost,'visited_states':len(distances)}
                if moves:
                    path=[];cursor=key
                    while cursor!=start:
                        previous,kind,k,event_index=parents[cursor]
                        path.append({'kind':kind,'transition':None if k is None else self.transitions[k].name,
                                     'event_index':event_index})
                        cursor=previous
                    result['moves']=list(reversed(path))
                return result
            i,s=divmod(key,size)
            candidates=[]
            for k,target in self.edges[s]:
                label=self.transitions[k].label
                if label is None:candidates.append((i*size+target,1,'tau',k,None))
                else:
                    if i<len(sequence) and label==sequence[i]:
                        candidates.append(((i+1)*size+target,0,'sync',k,i))
                    candidates.append((i*size+target,10000,'model',k,None))
            if i<len(sequence):candidates.append(((i+1)*size+s,10000,'log',None,i))
            for target,w,kind,k,event_index in candidates:
                if cost+w<distances.get(target,float('inf')):
                    distances[target]=cost+w
                    if moves:parents[target]=(key,kind,k,event_index)
                    heappush(queue,(cost+w,target))
        raise ValueError('No complete alignment')

    def verify(self, sequence, result):
        """Independently replay every move against actual P/T arc semantics."""
        state=list(self.start);i=cost=0;lookup={t.name:k for k,t in enumerate(self.transitions)}
        for move in result['moves']:
            kind=move['kind'];name=move['transition']
            if kind=='log':
                if name is not None or move['event_index']!=i:raise ValueError('Invalid log move')
                i+=1;cost+=10000;continue
            k=lookup[name];label=self.transitions[k].label
            if not all(state[p]>=w for p,w in self.pre[k]):raise ValueError('Disabled aligned transition')
            if kind=='sync':
                if i>=len(sequence) or sequence[i]!=label or move['event_index']!=i:raise ValueError('Invalid synchronous move')
                i+=1
            elif kind=='tau' and label is None:cost+=1
            elif kind=='model' and label is not None:cost+=10000
            else:raise ValueError('Invalid model move type')
            for p,w in self.pre[k]:state[p]-=w
            for p,w in self.post[k]:state[p]+=w
        if i!=len(sequence) or tuple(state)!=self.states[self.final] or cost!=result['cost']:
            raise ValueError('Alignment does not complete at stated cost')
        return True
