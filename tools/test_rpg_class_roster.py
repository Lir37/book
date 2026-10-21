#!/usr/bin/env python3
"""Regression for proposed 6x6 Eidos class roster and synthetic build fixtures."""
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "RPG_ЭЙДОС_ТЕСТОВЫЕ_СБОРКИ_48_6x6_v1.3_2026-10-21.json"
TXT = ROOT / "Книга про всякое, попытка 90123... (2).txt"
FB2 = ROOT / "Фон эпоса.fb2"
APPROVED = ROOT / "RPG_ЭЙДОС_УТВЕРЖДЁННЫЙ_КАТАЛОГ_140_НАВЫКОВ_v1.0_2026-10-21.json"
ATTRIBUTES = ("Сила","Ловкость","Выносливость","Живучесть","Восприятие","Дух")

class ClassRosterRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text(encoding="utf-8"))
        cls.builds=cls.data["builds"]

    def test_exact_six_six(self):
        roster=self.data["selectable_classes"]
        self.assertEqual(set(roster), {"arcanum","protocol"})
        self.assertEqual([len(roster[k]) for k in ("arcanum","protocol")], [6,6])
        self.assertEqual(len(self.builds),48)
        self.assertEqual(len({b["id"] for b in self.builds}),48)
        self.assertFalse(any(x["name"] in {"Некромант","Монах"} for r in roster.values() for x in r.values()))

    def test_early_baseline_each_class(self):
        for faction,roster in self.data["selectable_classes"].items():
            for class_id in roster:
                bs=[b for b in self.builds if b["faction"]==faction and b["class_id"]==class_id]
                self.assertTrue(any(b["specialization"] is None and b["level"]<20 for b in bs), (faction,class_id))

    def test_every_specialization_and_gates(self):
        for faction,roster in self.data["selectable_classes"].items():
            for cid,c in roster.items():
                for spec in c["specializations"]:
                    self.assertTrue(any(b["faction"]==faction and b["class_id"]==cid and b["specialization"]==spec and b["level"]>=20 for b in self.builds),(faction,cid,spec))
        for b in self.builds:
            if b["specialization"]:
                self.assertGreaterEqual(b["level"],20)
                self.assertIn(b["specialization"],self.data["selectable_classes"][b["faction"]][b["class_id"]]["specializations"])
            else:
                self.assertLess(b["level"],20)

    def test_no_fabricated_unlocks_or_stats(self):
        self.assertIn("NOT_CANONICAL",self.data["status"])
        self.assertEqual(len(self.data["legacy_140"]["branches"]),7)
        for b in self.builds:
            self.assertFalse(b["learned_skill_ids"])
            self.assertTrue(b["tested_skills_are_proposals"])
            self.assertEqual(set(b["attributes"]),set(ATTRIBUTES))
            self.assertTrue(all(isinstance(v,int) and v>0 for v in b["attributes"].values()))
            self.assertTrue(all(b[k] for k in ("scenario","equipment","tested_decision","countermeasure")))

    def test_140_approved_unchanged(self):
        d=json.loads(APPROVED.read_text(encoding="utf-8"))
        self.assertEqual(len(d["records"]),140)
        self.assertEqual(set(r["branch"] for r in d["records"]),set(self.data["legacy_140"]["branches"]))
        self.assertTrue(all(r["automatic_unlock"] is False and r["requires_training"] for r in d["records"]))

    def test_manuscript_and_fb2_synced_class_menu(self):
        txt=TXT.read_text(encoding="utf-8")
        fb2=FB2.read_text(encoding="utf-8")
        target="Паладины, маги, жрецы, лучники, разбойники и друиды."
        self.assertEqual(txt.count(target),1)
        self.assertEqual(fb2.count(target),1)
        self.assertNotIn("некроманты, монахи",txt)
        self.assertNotIn("некроманты, монахи",fb2)
        self.assertEqual(txt.count("Глава 3."),1)
        ET.fromstring(fb2)

if __name__=="__main__":
    unittest.main(verbosity=2)
