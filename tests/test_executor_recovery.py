import asyncio
import unittest
from backend.engines.executor import executor_engine


def state(goal='first'):
    return {'goal': goal, 'token_budget': 1000, 'token_used': 0,
            'agent_configs': [{'agent_id': a, 'subtask_id': a, 'system_prompt': a} for a in ['A','B']],
            'task_graph': {'subtasks': [{'id':'A','dependencies':[]},{'id':'B','dependencies':['A']}]}}


class ExecutorRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_dependency_order_reuse_and_input_invalidation(self):
        ran = []
        async def runner(config, goal, budget):
            if config['agent_id'] == 'B': self.assertIn('A', ran)
            ran.append(config['agent_id'])
            return {'tokens_used': 1, 'preliminary_result': goal}
        original = state()
        first = await executor_engine(original, runner)
        ran.clear()
        await executor_engine({**original, **first}, runner)
        self.assertEqual(ran, [])
        ran.clear()
        await executor_engine({**original, **first, 'goal':'new target'}, runner)
        self.assertEqual(ran, ['A','B'])
        ran.clear()
        changed = [{**original['agent_configs'][0], 'search_strategy':{'sources':['new']}}, original['agent_configs'][1]]
        await executor_engine({**original, **first, 'agent_configs':changed}, runner)
        self.assertEqual(ran, ['A','B'])

    async def test_failure_finishes_and_can_retry(self):
        async def broken(config, goal, budget):
            if config['agent_id']=='A': raise OSError('private detail must not appear')
            return {'tokens_used':1}
        first = await asyncio.wait_for(executor_engine(state(), broken), 1)
        self.assertEqual(first['agent_results']['A']['_error'], 'OSError')
        self.assertNotIn('private', str(first))
        ran=[]
        async def recovered(config, goal, budget):
            ran.append(config['agent_id'])
            return {'tokens_used':1}
        await executor_engine({**state(), **first}, recovered)
        self.assertEqual(ran,['A','B'])

    async def test_cycle_and_missing_dependency_rejected_before_execution(self):
        async def forbidden(*args): self.fail('runner must not be invoked')
        for graph in [{'subtasks':[{'id':'A','dependencies':['B']},{'id':'B','dependencies':['A']}]},
                      {'subtasks':[{'id':'A','dependencies':['missing']}]}]:
            with self.assertRaises(ValueError):
                await executor_engine({**state(),'task_graph':graph}, forbidden)
