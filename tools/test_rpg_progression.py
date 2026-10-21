#!/usr/bin/env python3
"""Canonical RPG regression tests for 26-chapter book and proposed levels 1..100."""
from __future__ import annotations
import re
import unittest
from pathlib import Path
from fractions import Fraction
from rpg_transition_contract import HUMAN, NotEnoughMana, transition_cost, mana_after, proportional_entry_cost, canonical_paid_entry_cost, paid_transition_cost
from rpg_mana_scenarios import trace_mana, compare_percentage_scenarios, FormActionUnavailable
from rpg_resource_model import (BEAST_REGEN_DIVISOR, APPROVED_FULL_HUMAN_REFILL_SECONDS, canonical_mana_cap, canonical_human_regen_rate, canonical_beast_regen_rate, proposed_mana_cap,
    candidate_human_regen_rate, effective_regen_rate, regenerated_mana,
    rounded_entry_cost, unassisted_entries_at_full_cap)

ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / 'Книга про всякое, попытка 90123... (2).txt'
SPECS = ROOT / 'RPG_ЭЙДОС_СПЕЦИФИКАЦИЯ_v0.3_ИССЛЕДОВАНИЕ_2026-10-20.md'
LEVELS = ROOT / 'RPG_ЭЙДОС_ТАБЛИЦА_УРОВНЕЙ_1-100_2026-10-20.md'


def cost(level: int) -> int:
    if not 1 <= level < 100:
        raise ValueError('level must be between 1 and 99')
    if level < 3:
        return 300
    return 25 * int((600 + 75 * (level - 3) ** 1.5) / 25 + 0.5)


def total_for(level: int) -> int:
    if not 1 <= level <= 100:
        raise ValueError('level must be between 1 and 100')
    return sum(cost(current) for current in range(1, level))


class RPGRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.book = BOOK.read_text(encoding='utf-8')
        cls.spec = SPECS.read_text(encoding='utf-8')
        cls.levels = LEVELS.read_text(encoding='utf-8')
        cls.chapters = re.split(r'(?m)^(?=Глава \d+(?:\.|\n))', cls.book)
        cls.chapters = [c for c in cls.chapters if re.match(r'^Глава \d+', c)]

    def test_early_cumulative_xp(self):
        self.assertEqual([total_for(k) for k in (1, 2, 3, 4, 5, 6)],
                         [0, 300, 600, 1200, 1875, 2675])

    def test_100_level_curve(self):
        self.assertEqual(total_for(100), 2803300)
        self.assertEqual(cost(99), 71150)
        self.assertTrue(all(cost(n + 1) >= cost(n) for n in range(3, 99)))
        self.assertTrue(all(cost(n) % 25 == 0 for n in range(3, 100)))
        self.assertIn('2 803 300', self.levels)

    def test_book_length_and_chapters(self):
        self.assertEqual(len(self.chapters), 26)
        self.assertGreaterEqual(len(self.book), 350000)
        self.assertIn('Осквернённые корни', self.chapters[11][:120])
        self.assertIn('Сердце под корнями', self.chapters[12][:120])

    def test_no_old_hp_or_stats(self):
        self.assertFalse(re.search(r'Здоровье:\s*\d+|(?:Интеллект|Удача)\s*[—:]', self.book))
        self.assertIn('Живучесть — 10.', self.book)
        self.assertIn('Восприятие — 13.', self.book)

    def test_earned_stat_points(self):
        self.assertIn('ловкость 14, дух 16', self.chapters[4])
        self.assertIn('выносливость 11, живучесть 11, дух 17', self.chapters[7])
        self.assertEqual(sum([8, 12, 10, 10, 13, 15]), 68)
        self.assertEqual(sum([8, 14, 10, 10, 13, 16]), 71)
        self.assertEqual(sum([8, 14, 11, 11, 13, 17]), 74)

    def test_form_costs_and_mastery(self):
        self.assertIn('Вход в звериную форму: 20% максимального запаса маны.', self.chapters[4])
        self.assertIn('Поддержание формы и возврат в человеческий облик бесплатны.', self.chapters[4])
        self.assertNotIn('5 единиц в секунду', self.book)
        self.assertIn('1,00 → 1,05', self.chapters[4])
        self.assertIn('на переключение форм снижен на 30%', self.chapters[5])
        self.assertIn('Мягкая смена', self.chapters[15])
        self.assertIn('Урсалон и Скайрэйвен снова стали серыми значками', self.chapters[5])

    def test_no_form_upkeep_or_automatic_timeout(self):
        self.assertIn('Вернуться можно даже при нулевой мане.', self.chapters[4])
        self.assertNotIn('Форма активна до отмены или исчерпания маны.', self.book)
        self.assertNotIn('Мана убывала даже здесь.', self.book)
        self.assertNotIn('форма рассеется сама', self.book)
        self.assertNotIn('пока не кончилась мана', self.book)

    def test_potion_still_has_a_reason(self):
        self.assertIn('Ману потратил на два превращения в Феллур, а силы — на погоню.', self.chapters[4])
        self.assertIn('Я не знал, хватит ли маны на ещё одно превращение', self.chapters[7])
        self.assertNotIn('Маны на ещё одно превращение в Феллур уже не хватало.', self.book)
        self.assertIn('полученного вчера зелья маны', self.chapters[7])
        self.assertIn('Мягкая смена', self.chapters[15])

    def test_new_author_decision_recorded(self):
        reference = (ROOT / 'RPG_ЭЙДОС_ПРЕВРАЩЕНИЯ_БЕЗ_РАСХОДА_ПОДДЕРЖАНИЯ_v0.5_2026-10-21.md').read_text('utf-8')
        self.assertIn('Само пребывание в форме не расходует ману', reference)
        self.assertIn('Открытые вопросы', reference)

    def test_free_return_even_with_zero_mana(self):
        """Mana affects entry into beast form, not the voluntary exit."""
        chapter = self.chapters[4]
        self.assertIn('возврат в человеческий облик бесплатны', chapter)
        self.assertIn('Вернуться можно даже при нулевой мане.', chapter)
        self.assertNotIn('Расход маны: при смене формы.', chapter)
        self.assertIn('Я вернул человеческий облик', chapter)

    def test_free_return_does_not_restore_injuries_or_xp(self):
        """Free return is not a loophole to erase injuries or reverse a death."""
        self.assertIn('На предплечье зияла рваная рана', self.chapters[22])
        self.assertIn('В игре погиб. Первый раз.', self.chapters[25])
        self.assertIn('выносливость 11, живучесть 11, дух 17', self.chapters[7])
        self.assertIn('Я вернулся в человеческий облик', self.chapters[12])

    def test_symbolic_free_return_at_any_mana(self):
        """Zero-mana return must work without retroactively choosing entry prices."""
        for balance in (False, True):
            for mana in (0, 1, 42):
                self.assertEqual(transition_cost('fellur', HUMAN, 17, balance), 0)
                self.assertEqual(mana_after('fellur', HUMAN, mana, 17, balance), mana)
        self.assertEqual(transition_cost('fellur', 'fellur', 17), 0)

    def test_symbolic_paid_entry_and_skill_discount(self):
        """Illustrative input 17 is NOT an author-approved mana price."""
        self.assertEqual(transition_cost(HUMAN, 'fellur', 17), Fraction(17))
        self.assertEqual(transition_cost(HUMAN, 'fellur', 17, True), Fraction(119, 10))
        self.assertEqual(transition_cost('fellur', 'ursalon', 17), Fraction(17))
        self.assertEqual(mana_after(HUMAN, 'fellur', 17, 17), 0)
        with self.assertRaises(NotEnoughMana):
            mana_after(HUMAN, 'fellur', 0, 17)

    def test_free_human_intermediary_cannot_make_beast_entry_free(self):
        """Returning free at zero mana does not fund entry to another form."""
        self.assertEqual(mana_after('fellur', HUMAN, 0, 17), 0)
        with self.assertRaises(NotEnoughMana):
            mana_after(HUMAN, 'skyraven', 0, 17)
        # A different beast target still requires an independently priced entry.
        with self.assertRaises(NotEnoughMana):
            mana_after('fellur', 'skyraven', 0, 17)

    def test_symbolic_potion_can_be_precautionary_not_a_forced_price(self):
        # At hypothetical full reserve, two entries for 5/10/15/20% of cap
        # never REQUIRE a potion. The scene must not claim an unknown price.
        for variant in compare_percentage_scenarios():
            self.assertGreater(variant['after_two_discounted_entries'], 0)
            self.assertGreater(variant['after_two_entries'], 0)
        self.assertIn('не собирался проверять это посреди схватки', self.chapters[7])

    def test_no_upkeep_even_after_long_beast_hold(self):
        before = trace_mana(125, 125, (('form', 'fellur'), ('hold', 30),
                                       ('form', HUMAN)), 20, True, human_regen_per_second=0)
        later = trace_mana(125, 125, (('form', 'fellur'), ('hold', 3600),
                                        ('form', HUMAN)), 20, True, human_regen_per_second=0)
        self.assertEqual(before[1], later[1])
        self.assertEqual(before[0], HUMAN)

    def test_empty_mana_return_is_possible(self):
        form, amount, _ = trace_mana(125, 25, (('form', 'fellur'),
                                                ('hold', 3600),
                                                ('form', HUMAN)), 25, human_regen_per_second=0)
        self.assertEqual((form, amount), (HUMAN, Fraction(0)))

    def test_free_intermediary_cannot_bypass_second_entry(self):
        with self.assertRaises(NotEnoughMana):
            trace_mana(125, 25, (('form', 'fellur'), ('form', HUMAN),
                                 ('form', 'fellur')), 25)

    def test_potion_restores_entry_without_requiring_upkeep(self):
        with self.assertRaises(NotEnoughMana):
            trace_mana(125, 20, (('form', 'fellur'), ('form', HUMAN),
                                 ('form', 'fellur')), 20, True)
        body, mana, ledger = trace_mana(
            125, 20, (('form', 'fellur'), ('form', HUMAN),
                      ('restore', 30), ('form', 'fellur')), 20, True)
        self.assertEqual(body, 'fellur')
        self.assertEqual(mana, Fraction(22))
        self.assertEqual(len(ledger), 4)

    def test_spells_consume_mana_without_drain_from_waiting(self):
        body, mana, _ = trace_mana(
            125, 125, (('form', 'fellur'), ('hold', 1000),
                       ('form', HUMAN), ('cast', 10)), 20,
            human_regen_per_second=0)
        # Return to human is mandatory before general druid spellcasting.
        self.assertEqual((body, mana), (HUMAN, Fraction(95)))

    def test_xp_in_book_not_recalculated(self):
        for token in ('150 / 300', '300/600', '450/600', '550/600',
                      '825/1200', '925/1200', '975/1200', '1075/1200'):
            self.assertIn(token, self.book)
        self.assertNotIn('2 803 300', self.book)  # full curve stays behind the scenes

    def test_death_stays_final(self):
        self.assertIn('сообщение о возрождении', self.chapters[24])
        self.assertIn('В игре погиб. Первый раз.', self.chapters[25])
        self.assertIn('целыми', self.chapters[24] + self.chapters[25])

    def test_post_death_experience_is_not_shown(self):
        # 1075/1200 is the last observed number (chapter 16), not a verified
        # value after the first death and unread penalty window in 25-26.
        self.assertIn('1075/1200', self.chapters[15])
        self.assertNotIn('1075/1200', self.chapters[24])
        self.assertNotIn('1075/1200', self.chapters[25])
        self.assertIn('Я не стал этого делать.', self.chapters[25])
        self.assertIn('не дочитав', self.chapters[24])

    def test_lost_knife_is_borrowed(self):
        self.assertIn('Запасного ножа не было', self.chapters[24])
        self.assertIn('Эльвира дала мне нож для зелени', self.chapters[25])

    def test_unapproved_mana_cap_not_in_book(self):
        self.assertNotIn('125 маны', self.book)

    def test_research_project_separation(self):
        self.assertIn('ПРОЕКТ', self.spec)
        self.assertIn('125 маны', self.spec)
        self.assertIn('v0.5', self.spec)  # newer rule explicitly overrides archived 5 mana/sec


    def test_approved_twenty_percent_maximum(self):
        self.assertEqual(proportional_entry_cost(125), Fraction(25))
        self.assertEqual(proportional_entry_cost(125, True), Fraction(35, 2))
        self.assertEqual(proportional_entry_cost(80, True), Fraction(56, 5))
        with self.assertRaises(ValueError):
            proportional_entry_cost(0)

    def test_discount_is_thirty_percent_of_paid_twenty_percent(self):
        self.assertEqual(proportional_entry_cost(100), 20)
        self.assertEqual(proportional_entry_cost(100, True), 14)
        self.assertEqual(transition_cost('fellur', HUMAN, 20, True), 0)

    def test_default_ledger_is_canonical_twenty_percent(self):
        beast, mana, _ = trace_mana(
            125, 125, (('form', 'fellur'), ('form', HUMAN),
                       ('form', 'fellur')), balance_of_chimeras=True)
        self.assertEqual((beast, mana), ('fellur', Fraction(89))) # 2 × ceil(125×0.14)

    def test_historical_fifteen_versus_approved_twenty(self):
        cap = Fraction(125)
        fifteen = cap * Fraction(15, 100) * Fraction(7, 10)
        twenty = proportional_entry_cost(cap, True)
        self.assertEqual((fifteen, twenty), (Fraction(105, 8), Fraction(35, 2)))
        self.assertEqual((cap // fifteen, cap // twenty), (9, 7))

    def test_different_mana_caps_without_inventing_spirit_formula(self):
        self.assertEqual(proportional_entry_cost(100), 20)
        self.assertEqual(proportional_entry_cost(160), 32)
        self.assertEqual(proportional_entry_cost(160, True), Fraction(112, 5))

    def test_general_druid_spell_is_human_only(self):
        with self.assertRaises(FormActionUnavailable):
            trace_mana(125, 125, (('form', 'fellur'), ('cast', 10)))
        body, mana, _ = trace_mana(
            125, 125, (('form', 'fellur'), ('form', HUMAN), ('cast', 10)))
        self.assertEqual((body, mana), (HUMAN, Fraction(90)))

    def test_form_specific_skill_must_match_beast_anatomy(self):
        with self.assertRaises(FormActionUnavailable):
            trace_mana(100, 100, (('form_skill', 4),))
        body, mana, _ = trace_mana(
            100, 100, (('form', 'fellur'), ('form_skill', 4),
                       ('hold', 3600), ('form', HUMAN)))
        self.assertEqual((body, mana), (HUMAN, Fraction(100)))  # 3600 game seconds restore full mana

    def test_potions_and_active_items_require_human(self):
        with self.assertRaises(FormActionUnavailable):
            trace_mana(125, 125, (('form', 'fellur'), ('restore', 30)))
        body, mana, _ = trace_mana(
            125, 25, (('form', 'fellur'), ('form', HUMAN),
                      ('restore', 30), ('form', 'fellur')))
        self.assertEqual((body, mana), ('fellur', Fraction(5)))

    def test_canonical_regeneration_is_on_by_default(self):
        _, natural, _ = trace_mana(100, 100, (('form', 'fellur'), ('hold', 9999)))
        _, explicit_none, _ = trace_mana(
            100, 100, (('form', 'fellur'), ('hold', 9999)),
            human_regen_per_second=0)
        self.assertEqual((natural, explicit_none), (Fraction(100), Fraction(80)))
        _, test_potion, _ = trace_mana(
            100, 100, (('form', 'fellur'), ('regen', 7), ('hold', 9999)),
            human_regen_per_second=0)
        self.assertEqual(test_potion, Fraction(87))

    def test_latest_author_decision_document_exists(self):
        p = ROOT / 'RPG_ЭЙДОС_РЕШЕНИЕ_20_ПРОЦЕНТОВ_И_ДОСТУП_В_ФОРМЕ_v0.6_2026-10-21.md'
        decision = p.read_text('utf-8')
        self.assertIn('20% расчётного максимума маны', decision)
        self.assertIn('14%', decision)
        self.assertIn('только в человеческом облике', decision)


    def test_author_approved_four_times_slower_recovery(self):
        self.assertEqual(BEAST_REGEN_DIVISOR, 4)
        self.assertEqual(effective_regen_rate(Fraction(5, 4), HUMAN), Fraction(5, 4))
        self.assertEqual(effective_regen_rate(Fraction(5, 4), 'fellur'), Fraction(5, 16))
        self.assertEqual(effective_regen_rate(Fraction(5, 4), 'ursalon'), Fraction(5, 16))

    def test_elapsed_time_recovers_mana_but_no_form_upkeep(self):
        # Cap 100, entry 20; an illustrative 0.25 mana/s HUMAN rate.
        body, mana, _ = trace_mana(
            100, 100, (('form', 'fellur'), ('hold', 20)),
            human_regen_per_second=Fraction(1, 4))
        self.assertEqual((body, mana), ('fellur', Fraction(325, 4)))  # 80 + 1.25
        body, human_mana, _ = trace_mana(
            100, 100, (('form', 'fellur'), ('form', HUMAN), ('hold', 20)),
            human_regen_per_second=Fraction(1, 4))
        self.assertEqual((body, human_mana), (HUMAN, Fraction(85)))

    def test_regeneration_only_depends_on_elapsed_time_not_upkeep(self):
        # The physical effort cost belongs to STAMINA, not the mana ledger.
        beast, remaining, _ = trace_mana(
            100, 30, (('form', 'fellur'), ('hold', 80)),
            human_regen_per_second=Fraction(1, 4))
        self.assertEqual((beast, remaining), ('fellur', Fraction(15)))
        self.assertEqual(regenerated_mana(100, 0, 80, Fraction(1, 4), HUMAN), 20)
        self.assertEqual(regenerated_mana(100, 0, 80, Fraction(1, 4), 'fellur'), 5)

    def test_zero_mana_free_return_then_human_recovery(self):
        body, remaining, _ = trace_mana(
            100, 20, (('form', 'fellur'), ('form', HUMAN), ('hold', 80),
                      ('form', 'fellur')),
            human_regen_per_second=Fraction(1, 4))
        self.assertEqual((body, remaining), ('fellur', Fraction(0)))

    def test_regeneration_never_exceeds_cap(self):
        self.assertEqual(regenerated_mana(125, 124, 9999, 3, HUMAN), 125)
        self.assertEqual(regenerated_mana(125, 124, 9999, 3, 'fellur'), 125)
        with self.assertRaises(ValueError):
            regenerated_mana(125, 126, 1, 1, HUMAN)
        with self.assertRaises(ValueError):
            regenerated_mana(125, 20, -1, 1, HUMAN)
        with self.assertRaises(ValueError):
            effective_regen_rate(0, 'fellur')

    def test_project_caps_spirit_and_level_are_explicit(self):
        self.assertEqual([proposed_mana_cap(s, lvl) for s, lvl in
                          ((15, 1), (16, 2), (17, 3))], [125, 132, 139])
        self.assertEqual(proposed_mana_cap(15, 1, 'flat'), 125)
        self.assertEqual(proposed_mana_cap(15, 1, 'spirit_heavy'), 130)
        self.assertEqual(proposed_mana_cap(17, 100, 'hybrid'), 333)
        with self.assertRaises(ValueError):
            proposed_mana_cap(15, 101)
        with self.assertRaises(ValueError):
            proposed_mana_cap(0, 1)

    def test_project_regen_ten_minutes_human_forty_beast(self):
        cap = proposed_mana_cap(15)
        rate = candidate_human_regen_rate(cap)
        self.assertEqual(regenerated_mana(cap, 0, 600, rate, HUMAN), cap)
        self.assertEqual(regenerated_mana(cap, 0, 600, rate, 'fellur'), cap / 4)
        self.assertEqual(regenerated_mana(cap, 0, 2400, rate, 'fellur'), cap)
        # Regenerate a 14%-of-cap entry in human vs beast
        price_without_rounding = rounded_entry_cost(cap, True, 'exact')
        self.assertEqual(regenerated_mana(cap, 0, 84, rate, HUMAN), price_without_rounding)
        self.assertEqual(regenerated_mana(cap, 0, 336, rate, 'fellur'), price_without_rounding)
        self.assertEqual(rounded_entry_cost(cap, True), 18)

    def test_rounding_is_applied_once_to_discounted_cost(self):
        self.assertEqual(rounded_entry_cost(125, True, 'exact'), Fraction(35, 2))
        self.assertEqual(rounded_entry_cost(125, True, 'ceil'), 18)
        self.assertEqual(rounded_entry_cost(125, True, 'half_up'), 18)
        self.assertEqual(rounded_entry_cost(106, True, 'ceil'), 15)
        self.assertEqual(rounded_entry_cost(106, False, 'ceil'), 22)
        self.assertEqual(unassisted_entries_at_full_cap(125, False), 5)
        self.assertEqual(unassisted_entries_at_full_cap(125, True), 6)
        with self.assertRaises(ValueError):
            rounded_entry_cost(125, True, 'bankers')

    def test_ratio_is_canonical_but_absolute_speed_remains_project(self):
        ratios = [effective_regen_rate(1, 'fellur') /
                  effective_regen_rate(1, HUMAN) for _ in (3, 4, 5)]
        self.assertEqual(ratios, [Fraction(1, 4)] * 3)
        # Changing the numerical base human rate does not change 1:4.
        for rate in (Fraction(1, 10), 1, 100):
            self.assertEqual(effective_regen_rate(rate, HUMAN),
                             4 * effective_regen_rate(rate, 'fellur'))

    def test_velarion_faction_regeneration_buff_keeps_four_to_one(self):
        # The 24h +10% faction bonus is already part of chapter 5 canon.
        self.assertIn('скорость восстановления маны повышена на 10% на 24 часа',
                      self.chapters[4])
        for base in (Fraction(1, 10), Fraction(125, 600), Fraction(9, 7)):
            boosted = base * Fraction(11, 10)
            self.assertEqual(effective_regen_rate(boosted, HUMAN),
                             4 * effective_regen_rate(boosted, 'fellur'))

    def test_new_regen_rule_is_in_book_and_project_docs(self):
        chapter = self.chapters[4]
        self.assertIn('20% максимального запаса маны', chapter)
        self.assertIn('в четыре раза медленнее', chapter)
        self.assertIn('Поддержание формы и возврат в человеческий облик бесплатны.', chapter)
        document = (ROOT / 'RPG_ЭЙДОС_РЕГЕНЕРАЦИЯ_v0.7_2026-10-21.md').read_text('utf8')
        self.assertIn('в четыре раза медленнее', document)
        self.assertIn('ПРОЕКТ', document)


    def test_v08_canonical_base_mana_caps_early_lir(self):
        self.assertEqual(APPROVED_FULL_HUMAN_REFILL_SECONDS, 600)
        for spirit, level, mana, normal_cost, discounted_cost in (
            (15, 1, 125, 25, 18), (16, 2, 132, 27, 19),
            (17, 3, 139, 28, 20),
        ):
            self.assertEqual(canonical_mana_cap(spirit, level), mana)
            self.assertEqual(canonical_paid_entry_cost(mana), normal_cost)
            self.assertEqual(canonical_paid_entry_cost(mana, True), discounted_cost)
        self.assertEqual(canonical_mana_cap(17, 100), 333)
        self.assertEqual(canonical_mana_cap(60, 100), 548)

    def test_v08_incremental_spirit_and_level_growth(self):
        self.assertEqual(canonical_mana_cap(16, 10) -
                         canonical_mana_cap(15, 10), 5)
        self.assertEqual(canonical_mana_cap(16, 11) -
                         canonical_mana_cap(16, 10), 2)

    def test_v08_exact_human_and_beast_recovery_rates(self):
        for cap in (125, 132, 139, 233, 548):
            self.assertEqual(canonical_human_regen_rate(cap), Fraction(cap, 600))
            self.assertEqual(canonical_beast_regen_rate(cap), Fraction(cap, 2400))
            self.assertEqual(canonical_human_regen_rate(cap),
                             canonical_beast_regen_rate(cap) * 4)

    def test_v08_billed_direct_beast_to_beast_and_free_exit(self):
        self.assertEqual(paid_transition_cost(HUMAN, "fellur", 139, True), 20)
        self.assertEqual(paid_transition_cost("fellur", "ursalon", 139, True), 20)
        self.assertEqual(paid_transition_cost("ursalon", HUMAN, 139, True), 0)
        self.assertEqual(paid_transition_cost("fellur", "fellur", 139, True), 0)
        body, mana, _ = trace_mana(139, 139, (
            ("form", "fellur"), ("form", "ursalon"), ("form", HUMAN)
        ), balance_of_chimeras=True)
        self.assertEqual((body, mana), (HUMAN, 99))

    def test_v08_level_three_temporary_trials_do_not_grant_forms(self):
        # v0.8 charges paid direct changes, but unlock is an external event.
        self.assertIn("Временный доступ испытания: Урсалон.", self.chapters[5])
        self.assertIn("Временный доступ испытания: Скайрэйвен.", self.chapters[5])
        self.assertIn("Урсалон и Скайрэйвен снова стали серыми значками", self.chapters[5])

    def test_v08_seventh_entry_requires_wait_or_external_restoration(self):
        self.assertEqual(unassisted_entries_at_full_cap(139, True), 6)
        six = tuple(x for _ in range(6)
                    for x in (("form", "fellur"), ("form", HUMAN)))
        _, after, _ = trace_mana(139, 139, six,
                                 balance_of_chimeras=True,
                                 human_regen_per_second=0)
        self.assertEqual(after, 19)
        with self.assertRaises(NotEnoughMana):
            trace_mana(139, 139, six + (("form", "fellur"),),
                       balance_of_chimeras=True,
                       human_regen_per_second=0)
        with_time = six + (("hold", Fraction(600, 139)), ("form", "fellur"))
        body, after_wait, _ = trace_mana(139, 139, with_time,
                                       balance_of_chimeras=True)
        self.assertEqual((body, after_wait), ("fellur", 0))

    def test_v08_fractional_regen_is_accumulated_not_zeroed(self):
        body, mana, _ = trace_mana(125, 125,
                                  (("form", "fellur"), ("hold", 1)),
                                  balance_of_chimeras=True)
        self.assertEqual((body, mana), ("fellur", Fraction(107) + Fraction(125, 2400)))
        self.assertGreater(mana, 107)
        self.assertLess(mana, 108)

    def test_v08_ten_minute_human_forty_minute_beast(self):
        for body in (HUMAN, "fellur"):
            seconds = 600 if body == HUMAN else 2400
            self.assertEqual(regenerated_mana(139, 0, seconds,
                             canonical_human_regen_rate(139), body), 139)
        body, mana, _ = trace_mana(
            139, 139, (("form", "fellur"), ("hold", 2400)))
        self.assertEqual((body, mana), ("fellur", 139))

    def test_v08_velarion_buff_preserves_ratio_and_shortens_wait(self):
        buff = Fraction(11, 10)
        base = canonical_human_regen_rate(139)
        boosted = base * buff
        self.assertEqual(effective_regen_rate(boosted, HUMAN),
                         4 * effective_regen_rate(boosted, 'fellur'))
        _, current, _ = trace_mana(
            139, 139, (("form", "fellur"), ("hold", 10)),
            balance_of_chimeras=True, regen_multiplier=buff)
        self.assertEqual(current, 119 + 10 * boosted / 4)

    def test_v08_rounding_discount_once(self):
        for maximum in (106, 125, 132, 139, 548):
            self.assertEqual(canonical_paid_entry_cost(maximum, True),
                             rounded_entry_cost(maximum, True, 'ceil'))
        self.assertEqual(canonical_paid_entry_cost(125, True), 18)
        self.assertNotEqual(Fraction(35, 2), canonical_paid_entry_cost(125, True))
        self.assertEqual(canonical_paid_entry_cost(548, True), 77)
        with self.assertRaises(ValueError):
            trace_mana(125, 125, (("hold", 1),), rounding_mode="unknown")

    def test_v08_text_preserves_dramatic_mana_constraints(self):
        self.assertIn('Вход в звериную форму: 20% максимального запаса маны.', self.chapters[4])
        self.assertIn('Восстановление маны в зверином облике: в четыре раза медленнее', self.chapters[4])
        self.assertIn('Ману потратил на два превращения в Феллур', self.chapters[4])
        self.assertIn('Я вернул человеческий облик', self.chapters[7])
        self.assertIn('Я не знал, хватит ли маны на ещё одно превращение', self.chapters[7])
        self.assertIn('Получен навык «Мягкая смена»', self.chapters[15])

    def test_v08_author_approved_spec_is_present(self):
        spec = (ROOT / 'RPG_ЭЙДОС_УТВЕРЖДЁННАЯ_ЭКОНОМИКА_МАНЫ_v0.8_2026-10-21.md').read_text('utf8')
        self.assertIn('УТВЕРЖДЕНО автором', spec)
        self.assertIn('600', spec)
        self.assertIn('2400', spec)
        self.assertIn('округлить ВВЕРХ', spec)

if __name__ == '__main__':
    unittest.main(verbosity=2)
