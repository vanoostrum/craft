# Copyright (C) 2026 Theo van Oostrum
"""One-shot runs one spec session and a parallel build lane, with no launch gate."""

import pytest

from tests.skill_text import ROOT, SKILLS, section, skill


def one_shot() -> str:
    """Return the One-shot section of `craft:next`."""
    return section(skill("next"), "One-shot")


def texts() -> dict[str, str]:
    """Return every skill text, `spec-review.md`, and the README, by name."""
    found = {
        path.parent.name: path.read_text(encoding="utf-8")
        for path in SKILLS.glob("*/SKILL.md")
    }
    found["spec-review.md"] = (SKILLS / "rules" / "spec-review.md").read_text(
        encoding="utf-8"
    )
    found["README.md"] = (ROOT / "README.md").read_text(encoding="utf-8")
    return found


@pytest.mark.parametrize("name", sorted(texts()))
def test_no_launch_gate_or_one_shot_phase_is_left(name: str) -> None:
    """No text names the launch gate as a stop, or a one-shot spec or build phase."""
    text = texts()[name].lower()
    assert "launch gate" not in text
    assert "spec phase" not in text
    assert "build phase" not in text


def test_old_launch_marker_only_where_it_is_read() -> None:
    """`🤖 Gate: launch` stays only in the steps that read it from older runs."""
    holders = {name for name, text in texts().items() if "🤖 Gate: launch" in text}
    assert holders == {"rules", "next", "build", "merge"}


def test_rules_chat_rule_names_the_needs_human_notice() -> None:
    """The Chat rule names the one-shot build lane and its Needs human exception."""
    rules = skill("rules")
    chat = rules.split("- **Chat.**", 1)[1].split("\n- **", 1)[0]
    assert "one-shot build lane" in chat
    assert "Needs human notice" in chat


def test_rules_and_readme_describe_parallel_lanes() -> None:
    """The overview in rules and the README describe both lanes running in parallel."""
    assert "in parallel" in section(skill("rules"), "One-shot mode")
    readme = section((ROOT / "README.md").read_text(encoding="utf-8"), "One-shot mode")
    assert "while" in readme
    assert "plan gate" in readme


def test_rules_send_the_needs_human_notice_at_once() -> None:
    """Each move of a one-shot ticket to Needs human tells the owner at once."""
    text = section(skill("rules"), "One-shot mode")
    notice = text.split("**Needs human notice.**", 1)[1].split("\n", 1)[0]
    for phrase in ("at once", "push notification", "what blocks it", "wait behind it"):
        assert phrase in notice


def test_next_defines_stuck_and_left_to_spec() -> None:
    """`craft:next` defines the two ticket sets that the one-shot rules use."""
    text = one_shot()
    assert "**stuck**" in text
    assert "**left to spec**" in text


def test_next_starts_one_spec_session() -> None:
    """The spec lane is one session, started only by the named callers."""
    step = one_shot().split("**Spec lane.**", 1)[1].split("\n2. ", 1)[0]
    assert "`Run craft:spec on the one-shot plan <plan key>.`" in step
    assert "left to spec and none is in **Specifying**" in step
    assert "never" in step
    assert "`craft:merge`" in step


def test_next_runs_the_build_lane_in_parallel() -> None:
    """The build lane starts a ready ticket whose blockers are Done, one at a time."""
    step = one_shot().split("**Build lane.**", 1)[1].split("\n3. ", 1)[0]
    assert "at the same time" in step
    assert "**Done**" in step
    assert "one ticket of the plan in **Building**" in step
    assert "Do not stop at the merge gate." in step
    assert "both directions" in step


def test_build_claims_a_one_shot_ticket() -> None:
    """A new one-shot build claims its ticket; a retry with a PR skips the claim."""
    step = skill("build").split("1. **Check that the ticket is ready.**", 1)[1]
    claim = step.split("**Claim.**", 1)[1].split("\n", 1)[0]
    assert "build-lane prompt" in claim
    assert "another ticket of the plan is in **Building**" in claim
    assert "skips the claim" in claim


def test_spec_loops_over_the_one_shot_plan() -> None:
    """`craft:spec` grills every one-shot ticket of the plan in one session."""
    text = section(skill("spec"), "One-shot")
    for phrase in (
        "one-shot plan ticket",
        "left to spec",
        "`mode=gated`",
        "run `craft:next`",
    ):
        assert phrase in text


def loop() -> str:
    """Return step 2 **Loop** of the One-shot section of `craft:spec`."""
    text = section(skill("spec"), "One-shot")
    return text.split("2. **Loop.**", 1)[1].split("\n3. **End.**", 1)[0]


def test_loop_does_not_take_the_next_ticket_early() -> None:
    """The next ticket waits until the current one leaves Specifying."""
    text = section(skill("spec"), "One-shot")
    assert "before the current one leaves **Specifying**" not in text
    step = loop()
    assert "at most one one-shot ticket in **Specifying**" in step
    assert (
        "Move, scout, or grill the next ticket only after the current one is in "
        "**Ready to build** or **Needs human**" in step
    )


def test_a_grill_round_holds_one_ticket() -> None:
    """A round in chat asks about the current ticket only."""
    step = loop()
    assert "A grill round asks about the current ticket only" in step
    assert "Never put another ticket's questions in it" in step


def test_loop_moves_other_specifying_tickets_back_to_todo() -> None:
    """Taking a ticket clears every other one-shot ticket out of Specifying."""
    step = loop()
    assert (
        "first move every other one-shot ticket in **Specifying** back to **Todo**"
        in step
    )


def test_spec_hands_off_to_scout_and_writer() -> None:
    """Each ticket gets a fresh spec scout and spec writer, one at a time."""
    text = section(skill("spec"), "One-shot")
    for phrase in (
        "spec scout",
        "spec writer",
        "decision log",
        "word for word",
        "one at a time",
    ):
        assert phrase in text


def test_one_shot_spec_gets_the_ticket_scope_review() -> None:
    """A one-shot spec is reviewed in ticket scope before Ready to build."""
    text = section(skill("spec"), "One-shot")
    review = text.split("**Review.**", 1)[1].split("\n", 1)[0]
    assert "ticket scope" in review
    assert "fifth FAIL" in review
    assert "**Needs human**" in review


def test_spec_reloads_after_compaction() -> None:
    """The spec session reloads its skills after a compaction."""
    text = section(skill("spec"), "One-shot")
    assert "compacted" in text
    assert "load `craft:rules` and `craft:spec` again" in text


def test_next_done_report_is_never_repeated() -> None:
    """The done report waits for the plan-scope review and is never posted twice."""
    step = one_shot().split("**Done report.**", 1)[1]
    assert "no `🤖 one-shot:` comment is newer" in step
    assert "`(default)` decision" in step
    assert "`🤖 one-shot: partial`" in step
    assert "stays open" in step


def test_replan_names_the_one_shot_rule() -> None:
    """The replan check sends a wrong ready spec back while grills still run."""
    replan = section(skill("next"), "Replan check")
    assert "while a one-shot ticket is left to spec" in replan
    assert "from a spec or a merge" in replan


def test_next_resumes_a_stuck_ticket() -> None:
    """The owner's "fixed" resumes a stuck ticket with no gates."""
    step = one_shot().split("**Resume.**", 1)[1].split("\n6. ", 1)[0]
    for phrase in (
        '"fixed"',
        '"resume"',
        "moved out of **Needs human**",
        "`🤖 resume: <cause> → <state>`",
        "**Ready to build**",
        "**Todo**",
        "start after the latest `🤖 resume:` comment",
    ):
        assert phrase in step


def test_notice_tells_how_to_resume() -> None:
    """The Needs human notice tells the owner how to resume."""
    step = one_shot().split("**Needs human notice.**", 1)[1].split("\n5. ", 1)[0]
    assert 'reply "fixed"' in step
    assert "waits for the next `craft:next`" in step


def test_plan_says_builds_start_as_specs_pass() -> None:
    """The plan gate is the last approval, and builds start as specs pass."""
    plan = skill("plan")
    gate = plan.split("10. **Gate.**", 1)[1].split("\n", 1)[0]
    assert "builds start as specs pass" in gate
    after = section(plan, "After approval")
    assert "done report" in after


def test_spec_review_names_both_one_shot_reviews() -> None:
    """`spec-review.md` names the ticket-scope and plan-scope reviews of one-shot."""
    review = (SKILLS / "rules" / "spec-review.md").read_text(encoding="utf-8")
    ticket = review.split("**Ticket scope.**", 1)[1].split("\n", 1)[0]
    plan = review.split("**Plan scope.**", 1)[1].split("\n", 1)[0]
    assert "one-shot" in ticket
    assert "one-shot" in plan


@pytest.mark.parametrize("role", ["spec scout", "spec writer"])
def test_spec_subagents_have_a_model(role: str) -> None:
    """`models.md` runs the spec scout and the spec writer on opus."""
    models = (SKILLS / "rules" / "models.md").read_text(encoding="utf-8")
    rows = [line for line in models.splitlines() if line.startswith(f"| {role} |")]
    assert len(rows) == 1
    assert rows[0].endswith("| opus |")


@pytest.mark.parametrize("name", ["build", "merge"])
def test_readiness_reads_the_latest_ticket_review(name: str) -> None:
    """Readiness reads the latest ticket-scope review, in any order to the spec."""
    text = skill(name)
    assert "the latest ticket-scope `🤖 spec review:` on the ticket is PASS" in text
    assert "PASS` after it" not in text


def test_spec_loop_reviews_before_success() -> None:
    """The loop posts the ticket-scope review before `🤖 spec: success`."""
    text = section(skill("spec"), "One-shot")
    assert text.index("**Review.**") < text.index("**Ready.**")


def test_loop_calls_next_for_the_build_lane_only() -> None:
    """The call after each ticket can never start a second spec session."""
    ready = section(skill("spec"), "One-shot").split("**Ready.**", 1)[1]
    ready = ready.split("\n", 1)[0]
    assert "build lane only" in ready
    step = one_shot().split("**Spec lane.**", 1)[1].split("\n2. ", 1)[0]
    assert "build lane only" in step
    assert "always keeps one ticket in **Specifying**" not in step


def test_failed_check_after_the_claim_releases_the_ticket() -> None:
    """A check that fails after the claim moves the ticket out of Building."""
    step = skill("build").split("1. **Check that the ticket is ready.**", 1)[1]
    claim = step.split("**Claim.**", 1)[1].split("\n", 1)[0]
    assert "back to **Ready to build**" in claim


def test_plan_scope_problems_stay_off_built_tickets() -> None:
    """A plan-scope problem goes only on tickets that go back to Todo."""
    step = one_shot().split("**Plan-scope review.**", 1)[1].split("\n4. ", 1)[0]
    assert "post each problem on each ticket it concerns" not in step
    assert "only on the tickets that go back to **Todo**" in step
