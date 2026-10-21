import unittest
from group_overlay_occurrences import group_occurrences


class GroupOverlayOccurrencesTest(unittest.TestCase):
    def report(self,times):
        return {'status':'completed','sample_fps':5,
                'occurrences':[{'start_seconds':t,'end_seconds_exclusive':t+1} for t in times]}

    def test_interior_graphics_do_not_become_separate_groups(self):
        r=group_occurrences(self.report([20,200,350,500,1500,1650,1800,2500]),100,2200)
        self.assertEqual(r['outside_occurrence_count'],2)
        self.assertEqual(len(r['groups']),2)
        self.assertEqual([g['interior_graphic_count'] for g in r['groups']],[1,1])
        self.assertEqual(sum(len(g['occurrences']) for g in r['groups']),6)
        self.assertTrue(all(g['status']=='candidate_temporal_group' for g in r['groups']))
        self.assertNotIn('timeline',r)

    def test_three_groups_are_preserved_instead_of_forcing_two_breaks(self):
        r=group_occurrences(self.report([200,300,1000,1100,1800,1900]),100,2200)
        self.assertEqual(len(r['groups']),3)
        self.assertTrue(all(g['status']=='candidate_temporal_group' for g in r['groups']))

    def test_long_adjacency_chain_is_ambiguous_instead_of_silently_split(self):
        r=group_occurrences(self.report([200,450,700,950]),100,1500)
        self.assertEqual(len(r['groups']),1)
        self.assertEqual(r['groups'][0]['status'],'ambiguous_overlong_cluster')

    def test_single_and_short_groups_are_not_promoted_to_breaks(self):
        r=group_occurrences(self.report([200,1000,1020]),100,1500)
        self.assertEqual([g['status'] for g in r['groups']],['isolated_graphic','short_cluster'])

    def test_boundary_straddling_is_retained_separately(self):
        r=group_occurrences(self.report([99.5,500]),100,500.5)
        self.assertEqual(len(r['straddling_occurrences']),2)
        self.assertEqual(r['groups'],[])

    def test_failed_scan_and_inconsistent_time_order_are_rejected(self):
        r=self.report([200]);r['status']='failed'
        with self.assertRaises(ValueError):group_occurrences(r,100,1000)
        with self.assertRaises(ValueError):group_occurrences(self.report([300,200]),100,1000)
        with self.assertRaises(ValueError):group_occurrences(self.report([200]),float('nan'),1000)


if __name__=='__main__':unittest.main()
