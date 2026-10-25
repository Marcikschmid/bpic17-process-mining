"""Readable XOR annotations; collapse only subtrees predicting one class."""
import json
import textwrap


def compact_rules(leaves):
    """Preserve the classifier partition while removing irrelevant leaf splits.

    A whole subtree can be replaced by its prefix iff all its leaves predict the
    same branch. Validate the prefix cover against EVERY original leaf.
    """
    def visit(group,depth):
        if len({leaf['class'] for leaf in group})==1:
            return [{'class':group[0]['class'],'predicates':group[0]['predicates'][:depth]}]
        if any(len(leaf['predicates'])<=depth for leaf in group):raise ValueError('Inconsistent decision tree leaves')
        feature={(leaf['predicates'][depth]['feature'],leaf['predicates'][depth]['threshold']) for leaf in group}
        if len(feature)!=1:raise ValueError('Inconsistent decision tree split')
        result=[]
        for op in ('<=','>'):
            children=[leaf for leaf in group if leaf['predicates'][depth]['op']==op]
            if not children:raise ValueError('Incomplete binary decision tree')
            result.extend(visit(children,depth+1))
        return result
    rules=visit(leaves,0)
    for leaf in leaves:
        matches=[r for r in rules if leaf['predicates'][:len(r['predicates'])]==r['predicates']]
        if len(matches)!=1 or matches[0]['class']!=leaf['class']:raise ValueError('Display rule changed classification')
    return rules


def predicate_text(predicate):
    feature=predicate['feature'].replace('case_','').replace('event_','last.')
    if '=' in feature and 0<=predicate['threshold']<1:
        name,value=feature.split('=',1)
        return f'{name} {"!=" if predicate["op"]=="<=" else "="} {json.dumps(value,ensure_ascii=False)}'
    return f'{feature} {predicate["op"]} {predicate["threshold"]:.8g}'


def annotation_text(gateway,width=68):
    """All rules appear inside the BPMN annotation, with matching branch IDs."""
    rules=compact_rules(gateway['leaves'])
    lines=[f'{gateway["id"]} | learned XOR rules',f'Test accuracy: {gateway["accuracy"]:.3f}', '']
    for flow in gateway['outgoing']:
        branch=gateway['branches'][flow]
        paths=[rule for rule in rules if rule['class']==flow]
        if not paths:
            lines.append(f'{branch}: FALSE (never predicted)')
        else:
            for rule in paths:
                text=' AND '.join(predicate_text(p) for p in rule['predicates']) or 'TRUE'
                lines.extend(textwrap.wrap(f'{branch}: {text}',width=width,subsequent_indent='    ',break_long_words=False,break_on_hyphens=False))
        lines.append('')
    lines.extend(['last. = last synchronized offer value', 'Learned associations; not bank policy.'])
    return '\n'.join(lines)
