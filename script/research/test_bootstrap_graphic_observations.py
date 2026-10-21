import unittest
from bootstrap_graphic_observations import plan_observations


class BootstrapGraphicObservationsTest(unittest.TestCase):
    def report(self,times):
        return {'status':'experimental','sample_fps':5,'index_limits_reached':True,
                'candidates':[{'occurrences':[{'core_start_seconds':t,'core_end_seconds':t+2} for t in group]}
                              for group in times]}

    def test_all_fragments_form_observation_zones_without_selecting_a_family(self):
        report=self.report([[10,200,430,850],[10,200,430],[10,430,850],[5,390,760],
                            [10.4,200.4,430.4,850.4]])
        grouping,windows=plan_observations(report,2500,25000)
        self.assertTrue(grouping['discovery_search_partial'])
        self.assertEqual(grouping['occurrence_origin'],'unclassified_discovery_pool')
        self.assertEqual(len(windows),4)
        self.assertEqual([g['first_graphic_seconds'] for g in grouping['groups']],[200,760])
        self.assertEqual(grouping['inside_occurrence_count'],5)
        self.assertTrue(all('candidate_role' not in w for w in windows))
        self.assertTrue(all(w['expected_frame_count']==1000 for w in windows))
        self.assertEqual(grouping['groups'][0]['occurrences'][0]['discovery_candidates'],[1,2,5])

    def test_context_is_clamped_to_exterior_bounds(self):
        _,windows=plan_observations(self.report([[110,180]]),2500,4749)
        self.assertEqual(windows[0]['first_decoded_frame'],2500)
        self.assertEqual(windows[-1]['end_decoded_frame_exclusive'],4750)
        self.assertTrue(all(25<=w['expected_frame_count']<=1500 for w in windows))

    def test_long_chains_and_too_many_zones_remain_unresolved(self):
        for times in [[[200,480,760,1040]],[[200,300,1000,1100,1800,1900,2600,2700]]]:
            with self.assertRaises(ValueError):plan_observations(self.report(times),0,80000)

    def test_invalid_pool_is_rejected(self):
        for times in [[[float('nan'),200]],[[200,300]]*101]:
            with self.assertRaises(ValueError):plan_observations(self.report(times),0,80000)


if __name__=='__main__':unittest.main()
