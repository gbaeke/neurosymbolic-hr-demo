% ============================================================
% HR leave policy, written as Answer Set Programming rules.
% The LLM never decides anything. It only supplies the facts.
% ============================================================

% --- Policy 1: entitlement = 20 days + 1 extra day per 5 full years of service
entitlement(E, 20 + (M / 12) / 5) :- tenure_months(E, M).
remaining(E, T - U)               :- entitlement(E, T), days_used(E, U).

% --- Hard rules (any violation => rejected)
violation(E, insufficient_balance) :- request(E, _, D), remaining(E, R), D > R.
violation(E, probation_max_2_days) :- request(E, _, D), tenure_months(E, M), M < 6, D > 2.
violation(E, finance_december_freeze) :- request(E, 12, _), department(E, finance).

% --- Soft rules (allowed, but a manager must sign off)
needs_approval(E, more_than_10_days) :- request(E, _, D), D > 10.
needs_approval(E, contractor)        :- request(E, _, _), contract(E, contractor).

% --- Decision: exactly one outcome per request
decision(E, rejected)         :- request(E, _, _), violation(E, _).
decision(E, manager_approval) :- request(E, _, _), not violation(E, _), needs_approval(E, _).
decision(E, approved)         :- request(E, _, _), not violation(E, _), not needs_approval(E, _).

#show decision/2.
#show violation/2.
#show needs_approval/2.
#show remaining/2.
