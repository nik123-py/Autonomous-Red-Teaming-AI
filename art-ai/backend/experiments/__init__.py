"""Research-grade evaluation harness for the ART-AI local attack MDP.

All components here operate on a self-contained, fully-specified, *enumerable*
Markov Decision Process that abstracts the local vulnerable lab. Because the MDP
is small and fully specified, an exact value-iteration optimum exists and is used
as the performance ceiling. Nothing here contacts any network target.
"""
