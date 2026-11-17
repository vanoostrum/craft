# Copyright (C) 2026 Theo van Oostrum
"""A one-shot build thread merges on the owner's merge approval, or escalates."""

from pathlib import Path

from tests.test_one_shot_lanes import one_shot, section, skill

ROOT = Path(__file__).resolve().parents[1]

SENTENCE = (
    "`Standing approval: craft may squash-merge the plan PR and each pull request"
    " for a ticket of one-shot plan <PLAN-KEY> into <base> of <owner/repo> once its"
    " fresh review passes and its required checks are green, in any thread, without"
    " asking me again.`"
)
RECORDED = "`🤖 Approved: plan (merge approval in chat, message <message id>)`"
ASKED = "`🤖 merge approval: asked`"
COMMAND = '`claude "Run craft:merge on <key>"`'


def numbered(text: str, label: str) -> str:
    """Return the numbered item that starts with `<n>. **<label>.**`."""
    return text.split(f"**{label}.**", 1)[1].split("\n", 1)[0]


def gate_step() -> str:
    """Return step 10 (Gate) of `craft:plan`."""
    return numbered(skill("plan"), "Gate")


def plan_merge_approval() -> str:
    """Return the Merge approval section of `craft:plan`."""
    return section(skill("plan"), "Merge approval")


def merge_check() -> str:
    """Return step 1 (Check the gate) of `craft:merge`, with its sub-lines."""
    return skill("merge").split("1. **Check the gate.**", 1)[1].split("\n2. ", 1)[0]


def merge_escalation() -> str:
    """Return the Escalation section of `craft:merge`."""
    return section(skill("merge"), "Escalation")


def rules_item(label: str) -> str:
    """Return the `- **<label>.**` rule of `craft:rules`."""
    return skill("rules").split(f"- **{label}.**", 1)[1].split("\n- **", 1)[0]


def rules_one_shot() -> str:
    """Return the One-shot mode section of `craft:rules`."""
    return section(skill("rules"), "One-shot mode")


def next_item(label: str) -> str:
    """Return a numbered item of the One-shot section of `craft:next`."""
    item = one_shot().split(f"**{label}.**", 1)[1]
    return item.split("\n6. ", 1)[0].split("\n5. ", 1)[0]


# Criterion 1 and 12: the gate shows the sentence, and it names the plan PR.
def test_plan_gate_shows_the_merge_approval_sentence() -> None:
    """The one-shot plan gate shows the sentence, filled in and ready to copy."""
    step = gate_step()
    assert SENTENCE in step
    assert "filled in" in step
    assert "approves the plan and the merges" in step


def test_sentence_names_the_plan_pr() -> None:
    """The sentence covers the plan PR merge after the plan gate."""
    assert "the plan PR" in SENTENCE
    assert SENTENCE in gate_step()


# Criterion 2 and Review focus 1: recording, and the bare "approve".
def test_plan_records_the_merge_approval() -> None:
    """The plan ticket gets the approval comment with the message id."""
    text = plan_merge_approval()
    assert RECORDED in text
    assert "id of the owner's message" in text


def test_rf1_bare_approve_asks_once_and_waits() -> None:
    """RF1: a bare approve or 👍 asks once for the sentence, and waits for it."""
    text = plan_merge_approval()
    assert 'bare "approve" or 👍' in text
    assert "ask once" in text
    assert ASKED in text
    assert "Do not ask again" in text
    assert "Wait for the sentence before **After approval**" in text


def test_rules_gate_names_the_merge_approval() -> None:
    """The gate rule says a one-shot plan gate is approved by the sentence too."""
    gate = rules_item("The gate")
    assert RECORDED in gate
    assert "**Merge approval** in `craft:plan`" in gate


def test_plan_after_approval_keeps_one_meaning() -> None:
    """After approval says the gate approves the plan PR merge, not 'merge approval'."""
    after = section(skill("plan"), "After approval")
    assert "also the merge approval for this PR" not in after
    assert "also approves the merge of this PR" in after
    assert "**Escalation** in `craft:merge`" in after


# Criterion 3: craft:next attaches the message to each build thread.
def test_next_attaches_the_merge_approval_to_build_threads() -> None:
    """The one-shot build lane asks the coordinator to attach the message by id."""
    lane = next_item("Build lane")
    assert "merge approval's message id" in lane
    assert "ask the coordinator to attach that message" in lane
    assert "`The attached message <message id> is the owner's merge approval.`" in (
        lane
    )


# Criterion 4, Review focus 2, 3 and 5: the check in step 1 of craft:merge.
def test_merge_checks_the_merge_approval_in_step_1() -> None:
    """Step 1 merges only with the owner's approval for this plan, repo, and base."""
    check = merge_check()
    assert "claude.ai project session" in check
    assert "merge approval for this ticket's plan, repo, and base" in check
    assert "go-ahead for this PR in this thread" in check
    assert "not the merge approval" in check


def test_rf2_no_attachment_escalates_without_trying() -> None:
    """RF2: without the attachment, the merge escalates once, and does not try."""
    check = merge_check()
    assert "do not try the merge" in check
    assert "`(no merge approval)`" in check
    escalation = merge_escalation()
    assert "Do not retry it" in escalation


def test_rf2_newer_no_approval_escalation_is_not_resumed() -> None:
    """RF2: a (no merge approval) escalation newer than the approval stays."""
    resume = next_item("Resume")
    assert "older than the latest `🤖 Approved: plan (merge approval" in resume
    assert "newer than the recorded approval stays" in resume


def test_rf3_other_plan_repo_or_base_does_not_count() -> None:
    """RF3: an approval for another plan, repo, or base does not count."""
    assert "names another plan, repo, or base does not count" in merge_check()


def test_rf5_terminal_skips_the_check_and_tries() -> None:
    """RF5: a terminal session skips the check and tries the merge."""
    assert "A terminal session has no message ids" in merge_check()
    assert "skips this check and tries the merge" in merge_check()


# Criterion 5: the merge tool.
def test_merge_uses_the_github_merge_tool() -> None:
    """Step 3 uses merge_pull_request with MCP tools, and gh api otherwise."""
    step = skill("merge").split("3. **Merge.**", 1)[1].split("\n4. ", 1)[0]
    assert "`merge_pull_request` tool" in step
    assert "`expectedHeadSha` set to the head SHA" in step
    assert "GitHub MCP tools" in step
    assert "Otherwise" in step
    assert "gh api -X PUT" in step
    assert "Craft-Issue: <TEAM>-<num>" in step
    github = rules_item("GitHub")
    assert "`merge_pull_request`" in github


# Criterion 6 and Review focus 4: a refused merge escalates, not a retry.
def test_refused_one_shot_merge_escalates() -> None:
    """A refused one-shot merge posts, moves, notifies, and runs craft:next."""
    escalation = merge_escalation()
    for phrase in (
        "🤖 merge: escalated — needs the owner's go-ahead (refused)",
        "link to this build thread",
        "**Needs human**",
        "send the Needs human notice",
        'reply "merge" in this thread to merge it',
        "run `craft:next`",
        "do not try another way",
    ):
        assert phrase in escalation


def test_rf4_escalation_is_not_a_failed_attempt() -> None:
    """RF4: the escalation leaves the retry count as it is."""
    assert "An escalation is not a failed attempt" in merge_escalation()
    assert "A refused merge is not a failed attempt" in rules_item("Retries")


# Criterion 7 and 13: only "merge" in the build thread moves it on.
def test_merge_in_the_build_thread_merges() -> None:
    """The owner's "merge" in the build thread reruns step 1 and step 2."""
    after = merge_escalation()
    assert 'owner\'s "merge" in the build thread' in after
    assert "Run step 1 and step 2 again" in after
    assert 'A "fixed" or "resume" for an escalated merge' in after
    assert "starts no merge session" in after


def test_next_resume_leaves_a_refused_merge() -> None:
    """Resume leaves a (refused) ticket where it is."""
    resume = next_item("Resume")
    assert "`(refused)`" in resume
    assert "leaves such a ticket where it is" in resume
    assert "starts no merge session" in resume


def test_notice_ends_with_merge_for_an_escalated_merge() -> None:
    """The Needs human notice asks for "merge" for an escalated merge."""
    notice = next_item("Needs human notice")
    assert 'reply "merge" in this thread to merge it' in notice
    assert "does not move an escalated merge on" in notice


def test_rules_and_readme_say_only_merge_moves_an_escalated_merge() -> None:
    """Rules item 5 and the README name "merge" in the build thread, not "fixed"."""
    item = rules_one_shot().split("5. **Needs human notice.**", 1)[1].split("\n6. ")[0]
    readme = section((ROOT / "README.md").read_text(encoding="utf-8"), "One-shot mode")
    for text in (item, readme):
        assert '"merge" in its build thread' in text
        assert COMMAND in text
        assert 'not with "fixed" or a change in Linear' in text


# Criterion 8: rules say which approval, and where it comes from.
def test_rules_one_shot_names_the_merge_approval_and_its_source() -> None:
    """One-shot mode names the merge approval, its source, and the attachment."""
    build_lane = rules_one_shot().split("3. **Build lane.**", 1)[1].split("\n4. ")[0]
    assert "**merge approval**" in build_lane
    assert "reply at the plan gate" in build_lane
    assert "attached by id to each one-shot build thread" in build_lane
    assert "`docs/adr/0007`" in build_lane


# Criterion 9: a running plan without an approval asks once in the notice.
def test_missing_merge_approval_is_asked_once_in_the_notice() -> None:
    """The first (no merge approval) notice asks for the sentence once."""
    escalation = merge_escalation()
    assert "also asks for the merge approval sentence" in escalation
    assert ASKED in escalation
    assert "no later notice asks again" in escalation


def test_recorded_approval_resumes_waiting_merges() -> None:
    """Once recorded, craft:next sends waiting merges back to In Review."""
    resume = next_item("Resume")
    assert "gets the merge approval sentence from the owner posts" in resume
    assert "**In Review**" in resume
    assert "`Run craft:merge on <key>.`" in resume


def test_chat_rule_carries_the_asks_in_the_notice() -> None:
    """The Chat rule puts both asks inside the Needs human notice."""
    chat = rules_item("Chat")
    assert "ask of an escalated merge" in chat
    assert "one ask for a missing merge approval" in chat


# Criterion 11: gated tickets and the plan PR.
def test_refused_gated_or_plan_merge_asks_in_the_thread() -> None:
    """A refused gated or plan PR merge asks for "merge" here, no Needs human."""
    gated = merge_escalation().split("**Gated ticket, or the plan PR.**", 1)[1]
    gated = gated.split("\n- ", 1)[0].split("\n\n", 1)[0]
    assert "🤖 plan: escalated" in gated
    assert 'reply "merge" in this thread' in gated
    assert "Do not move the ticket to **Needs human**" in gated


# Criterion 14: terminal escalations give the command.
def test_terminal_escalation_gives_the_command() -> None:
    """A terminal escalation names the command, and starting it merges at once."""
    escalation = merge_escalation()
    assert COMMAND in escalation
    assert "merges at once" in escalation


def test_rf2_no_recorded_approval_is_not_resumed_by_fixed() -> None:
    """RF2: "fixed" before the sentence arrives leaves a (no merge approval) merge."""
    escalated = next_item("Resume").split("**An escalated merge.**", 1)[1]
    escalated = escalated.split("\n   - ", 1)[0]
    assert "`(refused)`" in escalated
    assert "`(no merge approval)` with no newer recorded merge approval" in escalated
    assert "leaves such a ticket where it is" in escalated


def test_builds_start_without_a_recorded_merge_approval() -> None:
    """Criterion 9: a running plan with no recorded approval still builds."""
    assert "With no recorded merge approval, start the build anyway" in next_item(
        "Build lane"
    )


def test_merge_after_a_refused_plan_pr_merge_goes_on() -> None:
    """Criterion 11: "merge" for the plan PR merges it and starts the run."""
    after = merge_escalation().split("**After an escalation.**", 1)[1]
    assert "For the plan PR, run **Check CI** and **Merge** again" in after
    assert "**After approval** step 2 in `craft:plan`" in after


def test_late_merge_approval_does_not_rerun_after_approval() -> None:
    """Criterion 9: a running plan records the approval, and nothing else."""
    missing = next_item("Resume").split("**A missing merge approval.**", 1)[1]
    assert "without running **After approval** in `craft:plan` again" in missing
    assert "already ran" in plan_merge_approval()


def test_late_merge_approval_resumes_only_needs_human_tickets() -> None:
    """Criterion 9: the resume after a late approval is scoped and runs once."""
    missing = next_item("Resume").split("**A missing merge approval.**", 1)[1]
    assert "A ticket in **Needs human** whose latest escalation" in missing
    assert "needs no owner reply on the ticket" in missing
