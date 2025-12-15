# SLO Playbooks and Runbooks

## Service Level Objectives

### API Gateway
- **Availability SLO**: 99.9% (43.2 min downtime/month)
- **Latency SLO**: p95 < 200ms
- **Owner**: Platform Team
- **On-call**: ops-oncall@preciagro.com

### Conversational NLP (AgroLLM)
- **Availability SLO**: 99.5% (3.6 hours downtime/month)
- **Latency SLO**: p95 < 500ms
- **Owner**: AI/ML Team
- **On-call**: ai-oncall@preciagro.com

### Image Analysis
- **Availability SLO**: 99% (7.2 hours downtime/month)
- **Latency SLO**: p95 < 1000ms
- **Owner**: AI/ML Team

### Crop Intelligence
- **Availability SLO**: 99.5%
- **Latency SLO**: p95 < 300ms
- **Owner**: Data Science Team

---

## Runbooks

### APIGatewaySLOFastBurn

**Severity**: Critical  
**Trigger**: Error budget burning at >14x normal rate

**Steps**:
1. Check error rate dashboard
2. Identify failing endpoints
3. Review recent deployments (rollback if needed)
4. Check downstream service health
5. Scale up if capacity issue
6. Engage on-call team if unresolved in 10min

**Rollback**: `kubectl rollout undo deployment/api-gateway`

---

### ConversationalNLPSLOFastBurn

**Severity**: Critical  
**Trigger**: AgroLLM error budget burning fast

**Steps**:
1. Check LLM API status (OpenAI/Anthropic)
2. Review rate limits
3. Check context window errors
4. Verify RAG retrieval performance
5. Fallback to cached responses if needed

---

### HighLatency

**Severity**: Warning  
**Trigger**: p95 latency exceeding SLO

**Steps**:
1. Check database slow query log
2. Review Redis hit rate
3. Check for N+1 queries
4. Monitor CPU/memory
5. Consider caching improvements

---

## Error Budget Policy

- **Budget consumed < 50%**: Normal operations
- **Budget consumed 50-75%**: Review with team
- **Budget consumed 75-90%**: Freeze non-critical releases
- **Budget consumed > 90%**: Emergency mode - focus on reliability

## Escalation

1. Alert fires → On-call engineer (2min)
2. No response → Escalate to team lead (5min)
3. Critical SLO breach → Page manager (10min)
