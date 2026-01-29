-- ============================================================
--  被喷者档案 (roast_profiles)
-- ============================================================

CREATE TABLE IF NOT EXISTS roast_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    target_handle VARCHAR(64) UNIQUE NOT NULL,
    target_user_id VARCHAR(64),
    
    roast_count INTEGER DEFAULT 0 NOT NULL,
    unique_roasters INTEGER DEFAULT 0 NOT NULL,
    first_roasted_at TIMESTAMP WITH TIME ZONE,
    last_roasted_at TIMESTAMP WITH TIME ZONE,
    
    roast_themes JSONB DEFAULT '[]',
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_roast_profiles_target_handle ON roast_profiles(target_handle);
CREATE INDEX IF NOT EXISTS ix_roast_profiles_roast_count ON roast_profiles(roast_count);
CREATE INDEX IF NOT EXISTS ix_roast_profiles_last_roasted ON roast_profiles(last_roasted_at);


-- ============================================================
--  请求者画像 (requester_profiles)
-- ============================================================

CREATE TABLE IF NOT EXISTS requester_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    user_id VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) NOT NULL,
    
    request_count INTEGER DEFAULT 0 NOT NULL,
    favorite_targets JSONB DEFAULT '[]',
    
    is_registered BOOLEAN DEFAULT FALSE,
    oauth_access_token TEXT,
    oauth_refresh_token TEXT,
    last_login_at TIMESTAMP WITH TIME ZONE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_requester_profiles_user_id ON requester_profiles(user_id);
CREATE INDEX IF NOT EXISTS ix_requester_profiles_request_count ON requester_profiles(request_count);


-- ============================================================
--  复仇关系 (revenge_relations)
-- ============================================================

CREATE TABLE IF NOT EXISTS revenge_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    attacker_handle VARCHAR(64) NOT NULL,
    victim_handle VARCHAR(64) NOT NULL,
    
    attack_count INTEGER DEFAULT 1 NOT NULL,
    last_attack_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(attacker_handle, victim_handle)
);

CREATE INDEX IF NOT EXISTS ix_revenge_attacker ON revenge_relations(attacker_handle);
CREATE INDEX IF NOT EXISTS ix_revenge_victim ON revenge_relations(victim_handle);
