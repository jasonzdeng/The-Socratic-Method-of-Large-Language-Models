CREATE TABLE IF NOT EXISTS discussion_sessions (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_turns (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES discussion_sessions(id) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    prompt TEXT NOT NULL,
    response TEXT,
    reflections JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS tool_results (
    id SERIAL PRIMARY KEY,
    turn_id INTEGER NOT NULL REFERENCES agent_turns(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    output TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS judge_verdicts (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES discussion_sessions(id) ON DELETE CASCADE,
    judge_id TEXT NOT NULL,
    summary TEXT NOT NULL,
    open_issues JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discussion_events (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES discussion_sessions(id) ON DELETE CASCADE,
    phase TEXT NOT NULL,
    actor TEXT,
    payload JSONB DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    causal_turn_id INTEGER REFERENCES agent_turns(id) ON DELETE SET NULL,
    causal_tool_id INTEGER REFERENCES tool_results(id) ON DELETE SET NULL,
    causal_verdict_id INTEGER REFERENCES judge_verdicts(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_turns_session ON agent_turns(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_results_turn ON tool_results(turn_id);
CREATE INDEX IF NOT EXISTS idx_judge_verdicts_session ON judge_verdicts(session_id);
CREATE INDEX IF NOT EXISTS idx_events_session ON discussion_events(session_id);
