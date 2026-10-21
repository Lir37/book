#!/usr/bin/env python3
"""Author-approved v1.4 Eidos abilities, compatibility and NPC contract tests."""
import json
import math
import unittest
from pathlib import Path
from eidos_actor_builder import ROOT, read_data, validate_actor, usable_now

class NewRPGAbilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=read_data()
        cls.new=list(cls.data["new"].values())
        cls.old=list(cls.data["legacy"].values())
        cls.fixtures=json.loads((ROOT / "RPG_ЭЙДОС_ТЕСТОВЫЕ_СБОРКИ_48_6x6_v1.3_2026-10-21.json").read_text(encoding="utf-8"))

    def test_skill_catalog_114_109_and_140(self):
        self.assertEqual(len(self.new),223)
        self.assertEqual(len(self.old),140)
        self.assertEqual(len([r for r in self.new if r["faction"]=="arcanum"]),114)
        self.assertEqual(len([r for r in self.new if r["faction"]=="protocol"]),109)
        self.assertFalse(set(self.data["new"]) & set(self.data["legacy"]))

    def test_every_class_has_basics_and_specializations_have_five_tiers(self):
        expected_bases=[1,5,10,15]
        expected_specs=[20,30,50,75,100]
        for faction,roster in self.data["roster"].items():
            self.assertEqual(len(roster),6)
            for cls,c in roster.items():
                rows=[x for x in self.new if x["faction"]==faction and x["class_id"]==cls]
                self.assertEqual(sorted(x["level_gate"] for x in rows if x["specialization"] is None),expected_bases)
                for spec in c["specializations"]:
                    self.assertEqual(sorted(x["level_gate"] for x in rows if x["specialization"]==spec),expected_specs)

    def test_all_new_abilities_require_proven_training(self):
        for s in self.new:
            self.assertIs(s["automatic_unlock"],False)
            self.assertIs(s["requires_manual_unlock"],True)
            self.assertIs(s["requires_training"],True)
            self.assertTrue(s["effect"])
            self.assertTrue(s["countermeasures"])
            self.assertTrue(s["training_evidence"])
            self.assertEqual(s["prerequisites"],[] if s["level_gate"]==1 else s["prerequisites"])
            for dep in s["prerequisites"]:
                self.assertIn(dep,self.data["new"])
                self.assertLess(self.data["new"][dep]["level_gate"],s["level_gate"])

    def test_technomana_is_forbidden(self):
        for s in self.new:
            if s["faction"]=="protocol":
                self.assertEqual(s["resource"]["kind"],"physical")
                self.assertEqual(s["resource"].get("percent_max",0),0)

    def test_only_actual_spell_costs_mana(self):
        for s in self.new:
            if s["resource"]["kind"]=="mana":
                self.assertEqual(s["faction"],"arcanum")
                self.assertGreater(s["resource"]["percent_max"],0)
                self.assertLessEqual(s["resource"]["percent_max"],22)
            if s["class_id"] in ("archer","rogue"):
                self.assertNotEqual(s["resource"]["kind"],"mana")
        first=[x for x in self.new if x["class_id"]=="priest" and x["level_gate"]==1]
        self.assertEqual(len(first),1)
        self.assertEqual(first[0]["resource"]["kind"],"physical")

    def test_druid_canonical_forms_and_human_magic(self):
        for s in self.new:
            if s["class_id"]=="druid" and s["specialization"]=="Звериные тела":
                self.assertEqual(s["resource"]["kind"],"physiology")
            if s["class_id"]=="druid" and s["resource"]["kind"]=="mana":
                self.assertIs(s["resource"]["human_only"],True)
        self.assertIn("ceil",str(self.new))

    def test_legacy_entries_still_restrict_unlocks(self):
        self.assertTrue(all(x["automatic_unlock"] is False and x["requires_training"] for x in self.old))
        self.assertEqual(set(x["branch"] for x in self.old),{"druid_form","druid_nature","druid_craft","healer","tracker","fighter","engineer"})

    def test_fixtures_cover_all_classes_without_grants(self):
        builds=self.fixtures["builds"];self.assertEqual(len(builds),48)
        self.assertEqual(len([x for x in builds if x["faction"]=="arcanum"]),24)
        self.assertEqual(len([x for x in builds if x["faction"]=="protocol"]),24)
        self.assertTrue(all(x["learned_skill_ids"]==[] for x in builds))

    def test_character_rejects_untrained_high_level_skill(self):
        profile=self.fixtures["builds"][0]
        skill=next(s for s in self.new if s["class_id"]=="druid" and s["level_gate"]==100)
        actor={**profile,"learned_skill_ids":[skill["id"]],"training_evidence":{}}
        issues=validate_actor(actor,self.data)
        self.assertTrue(any("Insufficient level" in s for s in issues))
        self.assertTrue(any("Missing training evidence" in s for s in issues))

    def test_character_rejects_wrong_faction_and_specialization(self):
        src=self.fixtures["builds"][24]
        unrelated=next(s for s in self.new if s["class_id"]=="mage" and s["level_gate"]==1)
        bad={**src,"learned_skill_ids":[unrelated["id"]],"training_evidence":{unrelated["id"]:"observed demonstration"}}
        issues=validate_actor(bad,self.data)
        self.assertTrue(any("Wrong class/faction" in s for s in issues))

    def test_well_trained_core_skill_is_valid(self):
        src=self.fixtures["builds"][0]
        core=next(s for s in self.new if s["class_id"]=="druid" and s["level_gate"]==1 and s["specialization"] is None)
        actor={**src,"learned_skill_ids":[core["id"]],"training_evidence":{core["id"]:"mentor approved a demonstration"}}
        self.assertEqual(validate_actor(actor,self.data),[])
        self.assertFalse(usable_now(actor,core["id"],self.data)[0])
        actor["physical_conditions_ready"]=True
        self.assertTrue(usable_now(actor,core["id"],self.data)[0])

    def test_no_free_spellcasting_from_level(self):
        src=self.fixtures["builds"][0]
        item=next(s for s in self.new if s["class_id"]=="druid" and s["specialization"]=="Живая природа" and s["resource"]["kind"]=="mana")
        chain=[]
        cursor=item
        while True:
            chain.append(cursor)
            if not cursor["prerequisites"]:break
            cursor=self.data["new"][cursor["prerequisites"][0]]
        chain.reverse()
        actor={**src,"level":item["level_gate"],"specialization":"Живая природа","learned_skill_ids":[s["id"] for s in chain],"training_evidence":{s["id"]:"successfully trained in a real environment" for s in chain},"physical_conditions_ready":True,"mana_current":0}
        self.assertEqual(validate_actor(actor,self.data),[])
        self.assertFalse(usable_now(actor,item["id"],self.data)[0])
        actor["mana_current"]=10000
        actor["form"]="beast"
        self.assertFalse(usable_now(actor,item["id"],self.data)[0])
        actor["form"]="human"
        self.assertTrue(usable_now(actor,item["id"],self.data)[0])

    def test_protocol_no_technomana_in_actor(self):
        src=self.fixtures["builds"][24]
        bad={**src,"tech_mana":10}
        self.assertTrue(any("technomana" in s for s in validate_actor(bad,self.data)))

if __name__=="__main__":
    unittest.main(verbosity=2)
