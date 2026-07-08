from unittest.mock import patch, call

from scheduler import run_pipeline


def _run_with_mocks(
    beckers_return=(10, [1, 2]),
    kff_return=(20, [3]),
    triage_return=[1, 2],
    summarizer_return=[101, 102],
    discord_return=2,
):
    with patch('scheduler.run_scrape', return_value=beckers_return) as m_scrape, \
         patch('scheduler.run_monitor', return_value=kff_return) as m_monitor, \
         patch('scheduler.run_triage', return_value=triage_return) as m_triage, \
         patch('scheduler.run_summarizer', return_value=summarizer_return) as m_summ, \
         patch('scheduler.send_alerts', return_value=discord_return) as m_discord:
        run_pipeline()
        return m_scrape, m_monitor, m_triage, m_summ, m_discord


# ---------------------------------------------------------------------------
# Pipeline wiring — correct arguments flow downstream
# ---------------------------------------------------------------------------

def test_triage_receives_combined_article_ids():
    _, _, m_triage, _, _ = _run_with_mocks(
        beckers_return=(10, [1, 2]),
        kff_return=(20, [3, 4]),
    )
    args, _ = m_triage.call_args
    assert set(args[0]) == {1, 2, 3, 4}


def test_triage_receives_beckers_run_id():
    _, _, m_triage, _, _ = _run_with_mocks(beckers_return=(99, [1]))
    _, run_id = m_triage.call_args.args
    assert run_id == 99


def test_summarizer_receives_flagged_ids_from_triage():
    _, _, _, m_summ, _ = _run_with_mocks(triage_return=[5, 6])
    flagged, _ = m_summ.call_args.args
    assert flagged == [5, 6]


def test_summarizer_receives_same_run_id_as_triage():
    _, _, m_triage, m_summ, _ = _run_with_mocks(beckers_return=(42, [1]))
    assert m_triage.call_args.args[1] == m_summ.call_args.args[1]


def test_send_alerts_called_with_no_arguments():
    _, _, _, _, m_discord = _run_with_mocks()
    m_discord.assert_called_once_with()


# ---------------------------------------------------------------------------
# Empty cases — pipeline completes without error
# ---------------------------------------------------------------------------

def test_pipeline_completes_when_no_new_articles():
    _run_with_mocks(
        beckers_return=(1, []),
        kff_return=(2, []),
        triage_return=[],
        summarizer_return=[],
        discord_return=0,
    )


def test_pipeline_completes_when_triage_flags_nothing():
    _run_with_mocks(triage_return=[], summarizer_return=[], discord_return=0)


# ---------------------------------------------------------------------------
# All five stages are called on a normal run
# ---------------------------------------------------------------------------

def test_all_five_stages_called():
    m_scrape, m_monitor, m_triage, m_summ, m_discord = _run_with_mocks()
    assert m_scrape.call_count == 1
    assert m_monitor.call_count == 1
    assert m_triage.call_count == 1
    assert m_summ.call_count == 1
    assert m_discord.call_count == 1
