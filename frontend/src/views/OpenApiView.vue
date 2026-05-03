<template>
  <div class="openapi-view">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/>
            <path d="M7 8h.01M11 8h2M7 12h.01M11 12h6"/>
          </svg>
          Open API
        </h1>
        <span class="plan-badge elite">旗舰版</span>
      </div>
      <p class="page-desc">通过 API Key 将述标教练集成到您的内部系统或 CRM。</p>
    </div>

    <!-- Tab nav -->
    <div class="tab-nav">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
        <span v-if="tab.id === 'keys' && keys.length" class="tab-count">{{ keys.length }}</span>
        <span v-if="tab.id === 'webhooks' && webhooks.length" class="tab-count">{{ webhooks.length }}</span>
      </button>
    </div>

    <!-- API Keys Tab -->
    <div v-if="activeTab === 'keys'" class="tab-content">
      <div class="section-header">
        <h2>API Keys</h2>
        <button class="btn-primary" @click="showCreateKey = true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          创建 API Key
        </button>
      </div>

      <!-- Info box -->
      <div class="info-box">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
        <span>API Key 格式：<code>pc_live_&lt;64位随机串&gt;</code>。完整 Key 仅在创建时显示一次，请立即保存。</span>
      </div>

      <!-- Keys list -->
      <div v-if="loadingKeys" class="loading-state">
        <div class="spinner"></div> 加载中…
      </div>
      <div v-else-if="keys.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4"/>
        </svg>
        <p>还没有 API Key</p>
        <button class="btn-primary" @click="showCreateKey = true">创建第一个 Key</button>
      </div>
      <div v-else class="keys-table-wrap">
        <table class="keys-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>Key 前缀</th>
              <th>权限范围</th>
              <th>调用次数</th>
              <th>最近使用</th>
              <th>到期时间</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="key in keys" :key="key.id" :class="{ inactive: !key.is_active }">
              <td class="key-name">{{ key.name }}</td>
              <td><code class="key-prefix">{{ key.key_prefix }}…</code></td>
              <td>
                <span v-for="scope in key.scopes" :key="scope" class="scope-badge">{{ scope }}</span>
              </td>
              <td class="usage-count">{{ key.usage_count.toLocaleString() }}</td>
              <td class="dim">{{ key.last_used_at ? formatDate(key.last_used_at) : '从未' }}</td>
              <td class="dim">{{ key.expires_at ? formatDate(key.expires_at) : '永不' }}</td>
              <td>
                <span class="status-badge" :class="key.is_active ? 'active' : 'revoked'">
                  {{ key.is_active ? '活跃' : '已撤销' }}
                </span>
              </td>
              <td>
                <button
                  v-if="key.is_active"
                  class="btn-revoke"
                  @click="confirmRevoke(key)"
                >撤销</button>
                <span v-else class="dim">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Webhooks Tab -->
    <div v-if="activeTab === 'webhooks'" class="tab-content">
      <div class="section-header">
        <h2>Webhook 订阅</h2>
        <button class="btn-primary" @click="showCreateWebhook = true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          添加 Webhook
        </button>
      </div>

      <div v-if="loadingWebhooks" class="loading-state">
        <div class="spinner"></div> 加载中…
      </div>
      <div v-else-if="webhooks.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.3">
          <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
        </svg>
        <p>还没有 Webhook 订阅</p>
        <button class="btn-primary" @click="showCreateWebhook = true">添加第一个 Webhook</button>
      </div>
      <div v-else class="webhooks-list">
        <div v-for="wh in webhooks" :key="wh.id" class="webhook-card">
          <div class="webhook-header">
            <div class="webhook-url">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
              </svg>
              <span>{{ wh.url }}</span>
            </div>
            <div class="webhook-actions">
              <button class="btn-test" :disabled="testingWebhook === wh.id" @click="testWebhook(wh)">
                {{ testingWebhook === wh.id ? '测试中…' : '测试' }}
              </button>
              <button class="btn-revoke" @click="confirmDeleteWebhook(wh)">删除</button>
            </div>
          </div>
          <div class="webhook-events">
            <span v-for="ev in wh.events" :key="ev" class="event-badge">{{ ev }}</span>
          </div>
          <div v-if="webhookTestResults[wh.id]" class="test-result" :class="webhookTestResults[wh.id].success ? 'success' : 'error'">
            {{ webhookTestResults[wh.id].message }}
            <span v-if="webhookTestResults[wh.id].status_code"> ({{ webhookTestResults[wh.id].status_code }})</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Usage Tab -->
    <div v-if="activeTab === 'usage'" class="tab-content">
      <div class="section-header">
        <h2>API 用量统计</h2>
        <select v-model="usageDays" class="days-select" @change="loadUsage">
          <option :value="7">最近 7 天</option>
          <option :value="30">最近 30 天</option>
          <option :value="90">最近 90 天</option>
        </select>
      </div>

      <div v-if="loadingUsage" class="loading-state">
        <div class="spinner"></div> 加载中…
      </div>
      <div v-else-if="usageStats" class="usage-content">
        <!-- KPI cards -->
        <div class="usage-kpis">
          <div class="kpi-card">
            <div class="kpi-label">总调用次数</div>
            <div class="kpi-value">{{ usageStats.total_calls.toLocaleString() }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">错误次数</div>
            <div class="kpi-value error-val">{{ usageStats.error_count.toLocaleString() }}</div>
          </div>
          <div class="kpi-card">
            <div class="kpi-label">错误率</div>
            <div class="kpi-value" :class="usageStats.error_rate > 5 ? 'error-val' : ''">
              {{ usageStats.error_rate }}%
            </div>
          </div>
        </div>

        <!-- By endpoint -->
        <div class="usage-section">
          <h3>按端点统计（Top 10）</h3>
          <div v-if="usageStats.by_endpoint.length === 0" class="dim">暂无数据</div>
          <div v-else class="endpoint-bars">
            <div v-for="ep in usageStats.by_endpoint" :key="ep.endpoint" class="endpoint-row">
              <code class="ep-name">{{ ep.endpoint }}</code>
              <div class="ep-bar-wrap">
                <div class="ep-bar" :style="{ width: barWidth(ep.count) + '%' }"></div>
              </div>
              <span class="ep-count">{{ ep.count }}</span>
            </div>
          </div>
        </div>

        <!-- By key -->
        <div class="usage-section">
          <h3>按 Key 统计</h3>
          <div v-if="usageStats.by_key.length === 0" class="dim">暂无数据</div>
          <div v-else class="key-usage-list">
            <div v-for="item in usageStats.by_key" :key="item.api_key_id" class="key-usage-row">
              <span class="dim">Key #{{ item.api_key_id }}</span>
              <span>{{ item.count.toLocaleString() }} 次</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Docs Tab -->
    <div v-if="activeTab === 'docs'" class="tab-content">
      <div class="docs-content">
        <h2>快速上手</h2>
        <p class="dim">使用 API Key 通过 HTTP 请求调用述标教练数据。</p>

        <div class="doc-section">
          <h3>认证</h3>
          <p>在每个请求的 <code>Authorization</code> 头中携带您的 API Key：</p>
          <pre class="code-block">Authorization: Bearer pc_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</pre>
        </div>

        <div class="doc-section">
          <h3>示例：获取述标任务列表</h3>
          <pre class="code-block">curl https://your-domain.com/api/v1/pitch-tasks \
  -H "Authorization: Bearer pc_live_xxx..."</pre>
        </div>

        <div class="doc-section">
          <h3>Webhook 签名验证</h3>
          <p>每个 Webhook 请求都包含 <code>X-PitchCoach-Signature</code> 头，格式为 <code>sha256=&lt;hex&gt;</code>，使用您的 Signing Secret 对请求体进行 HMAC-SHA256 签名。</p>
          <pre class="code-block">import hmac, hashlib

def verify_signature(payload: bytes, secret: str, signature_header: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)</pre>
        </div>

        <div class="doc-section">
          <h3>可订阅事件</h3>
          <div class="events-table">
            <div v-for="ev in availableEvents" :key="ev.event" class="event-row">
              <code class="event-name">{{ ev.event }}</code>
              <span class="event-desc">{{ ev.description }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MCP Tools Tab -->
    <div v-if="activeTab === 'mcp'" class="tab-content">
      <div class="docs-content">
        <h2>MCP 工具接口</h2>
        <p class="dim">OpenClaw / Claude Agent 可通过标准 MCP 协议调用以下工具，实现与述标教练的智能联动。</p>

        <!-- Tool manifest link -->
        <div class="info-box" style="margin-bottom:20px">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>工具清单端点：<code>GET /api/v1/open-api/mcp/manifest</code>（需 JWT 或 API Key 认证）</span>
        </div>

        <!-- Tool cards -->
        <div class="mcp-tools-grid">
          <div class="mcp-tool-card">
            <div class="mcp-tool-header">
              <code class="mcp-tool-name">pitch_coach_check_readiness</code>
              <span class="mcp-scope-badge">read</span>
            </div>
            <p class="mcp-tool-desc">检查指定述标任务的 SOP 就绪状态（7步清单），返回每步完成情况、排练次数和最高分。</p>
            <div class="mcp-tool-section">
              <div class="mcp-param-label">输入参数</div>
              <div class="mcp-param-row"><code>task_id</code><span>integer · required</span><span class="mcp-param-desc">述标任务 ID</span></div>
            </div>
            <div class="mcp-tool-section">
              <div class="mcp-param-label">调用示例</div>
              <pre class="code-block">curl -X POST /api/v1/open-api/mcp/tools/pitch_coach_check_readiness \
  -H "Authorization: Bearer pc_live_xxx..." \
  -H "Content-Type: application/json" \
  -d '{"task_id": 42}'</pre>
            </div>
          </div>

          <div class="mcp-tool-card">
            <div class="mcp-tool-header">
              <code class="mcp-tool-name">pitch_coach_get_practice_status</code>
              <span class="mcp-scope-badge">read</span>
            </div>
            <p class="mcp-tool-desc">获取租户整体练习状态统计：总排练次数、平均分、活跃成员数、练习天数、最高分。</p>
            <div class="mcp-tool-section">
              <div class="mcp-param-label">输入参数</div>
              <div class="mcp-param-row"><code>days</code><span>integer · optional · default 30</span><span class="mcp-param-desc">统计近 N 天</span></div>
            </div>
            <div class="mcp-tool-section">
              <div class="mcp-param-label">调用示例</div>
              <pre class="code-block">curl -X POST /api/v1/open-api/mcp/tools/pitch_coach_get_practice_status \
  -H "Authorization: Bearer pc_live_xxx..." \
  -d '{"days": 7}'</pre>
            </div>
          </div>

          <div class="mcp-tool-card">
            <div class="mcp-tool-header">
              <code class="mcp-tool-name">pitch_coach_log_practice</code>
              <span class="mcp-scope-badge write">write</span>
            </div>
            <p class="mcp-tool-desc">从外部系统（CRM/OA）记录一次练习事件，统计用，不含真实录音。</p>
            <div class="mcp-tool-section">
              <div class="mcp-param-label">输入参数</div>
              <div class="mcp-param-row"><code>task_id</code><span>integer · required</span><span class="mcp-param-desc">述标任务 ID</span></div>
              <div class="mcp-param-row"><code>user_id</code><span>integer · required</span><span class="mcp-param-desc">用户 ID</span></div>
              <div class="mcp-param-row"><code>duration_sec</code><span>integer · required</span><span class="mcp-param-desc">练习时长（秒）</span></div>
              <div class="mcp-param-row"><code>score</code><span>number · optional</span><span class="mcp-param-desc">外部评分 0-100</span></div>
              <div class="mcp-param-row"><code>note</code><span>string · optional</span><span class="mcp-param-desc">练习备注</span></div>
            </div>
          </div>
        </div>

        <!-- OpenClaw config snippet -->
        <div class="doc-section" style="margin-top:28px">
          <h3>在 OpenClaw 中配置</h3>
          <p>将以下配置添加到 <code>.openclaw/mcp.yaml</code>：</p>
          <pre class="code-block">servers:
  pitch_coach:
    url: https://your-domain.com/api/v1/open-api/mcp/manifest
    auth:
      type: bearer
      token: pc_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx</pre>
        </div>
      </div>
    </div>

    <!-- ─── Modals ─────────────────────────────────────────────────────────── -->

    <!-- Create API Key modal -->
    <Teleport to="body">
      <div v-if="showCreateKey" class="modal-overlay" @click.self="showCreateKey = false">
        <div class="modal">
          <div class="modal-header">
            <h3>创建 API Key</h3>
            <button class="modal-close" @click="showCreateKey = false">✕</button>
          </div>
          <div class="modal-body">
            <!-- Show new key -->
            <div v-if="newKeyResult" class="new-key-box">
              <div class="new-key-warning">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                请立即复制并安全保存此 Key，关闭后将无法再次查看！
              </div>
              <div class="new-key-display">
                <code>{{ newKeyResult.key }}</code>
                <button class="btn-copy" @click="copyKey(newKeyResult!.key)">
                  {{ keyCopied ? '已复制 ✓' : '复制' }}
                </button>
              </div>
              <div class="new-key-meta">
                <span>名称：{{ newKeyResult.name }}</span>
                <span>权限：{{ newKeyResult.scopes.join(', ') }}</span>
                <span v-if="newKeyResult.expires_at">到期：{{ formatDate(newKeyResult.expires_at) }}</span>
                <span v-else>到期：永不</span>
              </div>
              <button class="btn-primary" style="width:100%;margin-top:12px" @click="closeNewKey">
                我已保存，关闭
              </button>
            </div>

            <!-- Create form -->
            <div v-else>
              <div class="form-group">
                <label>Key 名称 *</label>
                <input v-model="createKeyForm.name" type="text" class="form-input" placeholder="例如：我的 CRM 集成" />
              </div>
              <div class="form-group">
                <label>权限范围</label>
                <div class="scopes-checkboxes">
                  <label v-for="scope in availableScopes" :key="scope" class="scope-check">
                    <input type="checkbox" :value="scope" v-model="createKeyForm.scopes" />
                    {{ scope }}
                  </label>
                </div>
              </div>
              <div class="form-group">
                <label>有效期（天，留空=永不过期）</label>
                <input v-model.number="createKeyForm.expires_days" type="number" class="form-input" placeholder="365" min="1" />
              </div>
              <div v-if="createKeyError" class="form-error">{{ createKeyError }}</div>
            </div>
          </div>
          <div v-if="!newKeyResult" class="modal-footer">
            <button class="btn-cancel" @click="showCreateKey = false">取消</button>
            <button class="btn-primary" :disabled="creatingKey" @click="createKey">
              {{ creatingKey ? '创建中…' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Create Webhook modal -->
    <Teleport to="body">
      <div v-if="showCreateWebhook" class="modal-overlay" @click.self="showCreateWebhook = false">
        <div class="modal">
          <div class="modal-header">
            <h3>添加 Webhook</h3>
            <button class="modal-close" @click="showCreateWebhook = false">✕</button>
          </div>
          <div class="modal-body">
            <div v-if="newWebhookResult" class="new-key-box">
              <div class="new-key-warning">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
                  <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
                请立即保存 Signing Secret，用于验证 Webhook 签名！
              </div>
              <div class="new-key-display">
                <code>{{ newWebhookResult.signing_secret }}</code>
                <button class="btn-copy" @click="copySecret(newWebhookResult!.signing_secret)">
                  {{ secretCopied ? '已复制 ✓' : '复制' }}
                </button>
              </div>
              <div class="new-key-meta">
                <span>URL：{{ newWebhookResult.url }}</span>
                <span>事件：{{ newWebhookResult.events.length }} 个</span>
              </div>
              <button class="btn-primary" style="width:100%;margin-top:12px" @click="closeNewWebhook">
                我已保存，关闭
              </button>
            </div>

            <div v-else>
              <div class="form-group">
                <label>Endpoint URL *</label>
                <input v-model="createWebhookForm.url" type="url" class="form-input" placeholder="https://your-server.com/webhook" />
              </div>
              <div class="form-group">
                <label>订阅事件</label>
                <div class="events-checkboxes">
                  <label v-for="ev in availableEvents" :key="ev.event" class="scope-check">
                    <input type="checkbox" :value="ev.event" v-model="createWebhookForm.events" />
                    <span><code>{{ ev.event }}</code> — {{ ev.description }}</span>
                  </label>
                </div>
              </div>
              <div class="form-group">
                <label>Signing Secret（留空自动生成）</label>
                <input v-model="createWebhookForm.secret" type="text" class="form-input" placeholder="自动生成" />
              </div>
              <div v-if="createWebhookError" class="form-error">{{ createWebhookError }}</div>
            </div>
          </div>
          <div v-if="!newWebhookResult" class="modal-footer">
            <button class="btn-cancel" @click="showCreateWebhook = false">取消</button>
            <button class="btn-primary" :disabled="creatingWebhook" @click="createWebhook">
              {{ creatingWebhook ? '创建中…' : '创建' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirm revoke key dialog -->
    <Teleport to="body">
      <div v-if="revokeTarget" class="modal-overlay" @click.self="revokeTarget = null">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3>撤销 API Key</h3>
          </div>
          <div class="modal-body">
            <p>确定要撤销 <strong>{{ revokeTarget.name }}</strong>（<code>{{ revokeTarget.key_prefix }}…</code>）吗？</p>
            <p class="dim">撤销后所有使用此 Key 的请求将立即失败，此操作不可恢复。</p>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="revokeTarget = null">取消</button>
            <button class="btn-danger" :disabled="revoking" @click="doRevoke">
              {{ revoking ? '撤销中…' : '确认撤销' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirm delete webhook dialog -->
    <Teleport to="body">
      <div v-if="deleteWebhookTarget" class="modal-overlay" @click.self="deleteWebhookTarget = null">
        <div class="modal modal-sm">
          <div class="modal-header">
            <h3>删除 Webhook</h3>
          </div>
          <div class="modal-body">
            <p>确定要删除此 Webhook 吗？</p>
            <p class="dim">{{ deleteWebhookTarget.url }}</p>
          </div>
          <div class="modal-footer">
            <button class="btn-cancel" @click="deleteWebhookTarget = null">取消</button>
            <button class="btn-danger" :disabled="deletingWebhook" @click="doDeleteWebhook">
              {{ deletingWebhook ? '删除中…' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  openApiApi,
  type ApiKeySummary,
  type ApiKeyCreated,
  type WebhookSummary,
  type WebhookCreated,
  type ApiUsageStats,
  type AvailableEvent,
  type WebhookTestResult,
} from '@/api/openApi'

// ─── Tab state ────────────────────────────────────────────────────────────────

const tabs = [
  { id: 'keys', label: '🔑 API Keys' },
  { id: 'webhooks', label: '⚡ Webhooks' },
  { id: 'usage', label: '📊 用量统计' },
  { id: 'docs', label: '📖 文档' },
  { id: 'mcp', label: '🤖 MCP 工具' },
]
const activeTab = ref('keys')

// ─── API Keys ─────────────────────────────────────────────────────────────────

const keys = ref<ApiKeySummary[]>([])
const loadingKeys = ref(false)
const showCreateKey = ref(false)
const creatingKey = ref(false)
const createKeyError = ref('')
const newKeyResult = ref<ApiKeyCreated | null>(null)
const keyCopied = ref(false)
const revokeTarget = ref<ApiKeySummary | null>(null)
const revoking = ref(false)

const availableScopes = ['read', 'write', 'webhook', 'admin']

const createKeyForm = ref({
  name: '',
  scopes: ['read'] as string[],
  expires_days: null as number | null,
})

async function loadKeys() {
  loadingKeys.value = true
  try {
    const res = await openApiApi.listKeys()
    keys.value = res.data
  } catch {
    // ignore
  } finally {
    loadingKeys.value = false
  }
}

async function createKey() {
  createKeyError.value = ''
  if (!createKeyForm.value.name.trim()) {
    createKeyError.value = '请输入 Key 名称'
    return
  }
  creatingKey.value = true
  try {
    const res = await openApiApi.createKey({
      name: createKeyForm.value.name.trim(),
      scopes: createKeyForm.value.scopes,
      expires_days: createKeyForm.value.expires_days || null,
    })
    newKeyResult.value = res.data
    await loadKeys()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    createKeyError.value = err?.response?.data?.detail || '创建失败，请重试'
  } finally {
    creatingKey.value = false
  }
}

function closeNewKey() {
  newKeyResult.value = null
  showCreateKey.value = false
  createKeyForm.value = { name: '', scopes: ['read'], expires_days: null }
  keyCopied.value = false
}

async function copyKey(key: string) {
  await navigator.clipboard.writeText(key)
  keyCopied.value = true
  setTimeout(() => { keyCopied.value = false }, 2000)
}

function confirmRevoke(key: ApiKeySummary) {
  revokeTarget.value = key
}

async function doRevoke() {
  if (!revokeTarget.value) return
  revoking.value = true
  try {
    await openApiApi.revokeKey(revokeTarget.value.id)
    revokeTarget.value = null
    await loadKeys()
  } finally {
    revoking.value = false
  }
}

// ─── Webhooks ─────────────────────────────────────────────────────────────────

const webhooks = ref<WebhookSummary[]>([])
const loadingWebhooks = ref(false)
const showCreateWebhook = ref(false)
const creatingWebhook = ref(false)
const createWebhookError = ref('')
const newWebhookResult = ref<WebhookCreated | null>(null)
const secretCopied = ref(false)
const deleteWebhookTarget = ref<WebhookSummary | null>(null)
const deletingWebhook = ref(false)
const testingWebhook = ref<number | null>(null)
const webhookTestResults = ref<Record<number, WebhookTestResult>>({})

const createWebhookForm = ref({
  url: '',
  events: [] as string[],
  secret: '',
})

async function loadWebhooks() {
  loadingWebhooks.value = true
  try {
    const res = await openApiApi.listWebhooks()
    webhooks.value = res.data
  } catch {
    // ignore
  } finally {
    loadingWebhooks.value = false
  }
}

async function createWebhook() {
  createWebhookError.value = ''
  const url = createWebhookForm.value.url.trim()
  if (!url) {
    createWebhookError.value = '请输入 Endpoint URL'
    return
  }
  creatingWebhook.value = true
  try {
    const res = await openApiApi.createWebhook({
      url,
      events: createWebhookForm.value.events.length > 0 ? createWebhookForm.value.events : undefined,
      secret: createWebhookForm.value.secret.trim() || undefined,
    })
    newWebhookResult.value = res.data
    await loadWebhooks()
  } catch (e: unknown) {
    const err = e as { response?: { data?: { detail?: string } } }
    createWebhookError.value = err?.response?.data?.detail || '创建失败，请重试'
  } finally {
    creatingWebhook.value = false
  }
}

function closeNewWebhook() {
  newWebhookResult.value = null
  showCreateWebhook.value = false
  createWebhookForm.value = { url: '', events: [], secret: '' }
  secretCopied.value = false
}

async function copySecret(secret: string) {
  await navigator.clipboard.writeText(secret)
  secretCopied.value = true
  setTimeout(() => { secretCopied.value = false }, 2000)
}

function confirmDeleteWebhook(wh: WebhookSummary) {
  deleteWebhookTarget.value = wh
}

async function doDeleteWebhook() {
  if (!deleteWebhookTarget.value) return
  deletingWebhook.value = true
  try {
    await openApiApi.deleteWebhook(deleteWebhookTarget.value.id)
    deleteWebhookTarget.value = null
    await loadWebhooks()
  } finally {
    deletingWebhook.value = false
  }
}

async function testWebhook(wh: WebhookSummary) {
  testingWebhook.value = wh.id
  try {
    const res = await openApiApi.testWebhook(wh.id)
    webhookTestResults.value[wh.id] = res.data
  } catch {
    webhookTestResults.value[wh.id] = {
      success: false,
      url: wh.url,
      message: '请求失败，请检查服务器是否可达',
    }
  } finally {
    testingWebhook.value = null
  }
}

// ─── Usage stats ──────────────────────────────────────────────────────────────

const usageStats = ref<ApiUsageStats | null>(null)
const loadingUsage = ref(false)
const usageDays = ref(30)

async function loadUsage() {
  loadingUsage.value = true
  try {
    const res = await openApiApi.getUsage(usageDays.value)
    usageStats.value = res.data
  } catch {
    // ignore
  } finally {
    loadingUsage.value = false
  }
}

const maxEndpointCount = computed(() => {
  if (!usageStats.value || usageStats.value.by_endpoint.length === 0) return 1
  return Math.max(...usageStats.value.by_endpoint.map(e => e.count))
})

function barWidth(count: number): number {
  return Math.round(count / maxEndpointCount.value * 100)
}

// ─── Available events ─────────────────────────────────────────────────────────

const availableEvents = ref<AvailableEvent[]>([])

async function loadAvailableEvents() {
  try {
    const res = await openApiApi.availableEvents()
    availableEvents.value = res.data
    // Pre-select all events for new webhook form
    createWebhookForm.value.events = res.data.map(e => e.event)
  } catch {
    // ignore
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// ─── Init ─────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([loadKeys(), loadWebhooks(), loadUsage(), loadAvailableEvents()])
})
</script>

<style scoped>
.openapi-view {
  padding: 32px;
  max-width: 1100px;
}

/* Header */
.page-header { margin-bottom: 28px; }
.header-left { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.page-title { font-size: 22px; font-weight: 700; color: #1a1a2e; display: flex; align-items: center; gap: 10px; margin: 0; }
.page-title svg { color: #6366F1; }
.page-desc { color: #6b7280; font-size: 14px; margin: 0; }
.plan-badge { font-size: 11px; font-weight: 600; padding: 3px 8px; border-radius: 12px; }
.plan-badge.elite { background: linear-gradient(135deg, #6366F1, #8B5CF6); color: white; }

/* Tabs */
.tab-nav { display: flex; gap: 4px; border-bottom: 1px solid #e5e7eb; margin-bottom: 24px; }
.tab-btn {
  padding: 10px 18px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-size: 14px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
  margin-bottom: -1px;
}
.tab-btn:hover { color: #374151; }
.tab-btn.active { color: #6366F1; border-bottom-color: #6366F1; }
.tab-count { background: #e0e7ff; color: #6366F1; font-size: 11px; font-weight: 700; padding: 1px 6px; border-radius: 10px; }

/* Section header */
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.section-header h2 { font-size: 16px; font-weight: 600; color: #1a1a2e; margin: 0; }

/* Buttons */
.btn-primary {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: #6366F1;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-primary:hover { background: #5558e3; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-revoke {
  padding: 4px 10px;
  background: #fee2e2;
  color: #dc2626;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-revoke:hover { background: #fecaca; }

.btn-test {
  padding: 4px 10px;
  background: #e0e7ff;
  color: #6366F1;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-test:hover { background: #c7d2fe; }
.btn-test:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-danger {
  padding: 8px 16px;
  background: #dc2626;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-danger:hover { background: #b91c1c; }
.btn-danger:disabled { opacity: 0.6; cursor: not-allowed; }

.btn-cancel {
  padding: 8px 16px;
  background: #f3f4f6;
  color: #374151;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
}
.btn-cancel:hover { background: #e5e7eb; }

.btn-copy {
  padding: 4px 10px;
  background: #6366F1;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

/* Info box */
.info-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  font-size: 13px;
  color: #1e40af;
  margin-bottom: 20px;
}
.info-box code { background: #dbeafe; padding: 1px 5px; border-radius: 4px; font-family: monospace; }

/* Keys table */
.keys-table-wrap { overflow-x: auto; }
.keys-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.keys-table th {
  text-align: left;
  padding: 10px 12px;
  color: #6b7280;
  font-weight: 600;
  font-size: 12px;
  border-bottom: 1px solid #e5e7eb;
  white-space: nowrap;
}
.keys-table td {
  padding: 12px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}
.keys-table tr.inactive td { opacity: 0.5; }
.key-name { font-weight: 600; color: #1a1a2e; }
.key-prefix { background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px; }
.scope-badge { display: inline-block; background: #ede9fe; color: #7c3aed; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 600; margin-right: 4px; }
.usage-count { font-weight: 600; color: #374151; }
.status-badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
.status-badge.active { background: #dcfce7; color: #16a34a; }
.status-badge.revoked { background: #fee2e2; color: #dc2626; }

/* Webhooks */
.webhooks-list { display: flex; flex-direction: column; gap: 12px; }
.webhook-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 16px;
  background: white;
}
.webhook-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; gap: 12px; }
.webhook-url { display: flex; align-items: center; gap: 8px; color: #374151; font-size: 13px; font-weight: 500; min-width: 0; }
.webhook-url span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.webhook-actions { display: flex; gap: 8px; flex-shrink: 0; }
.webhook-events { display: flex; flex-wrap: wrap; gap: 6px; }
.event-badge { display: inline-block; background: #f3f4f6; color: #374151; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-family: monospace; }
.test-result { margin-top: 10px; padding: 8px 12px; border-radius: 6px; font-size: 12px; }
.test-result.success { background: #dcfce7; color: #16a34a; }
.test-result.error { background: #fee2e2; color: #dc2626; }

/* Usage */
.usage-kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px; }
.kpi-card { background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 20px; text-align: center; }
.kpi-label { font-size: 12px; color: #6b7280; font-weight: 600; margin-bottom: 8px; }
.kpi-value { font-size: 32px; font-weight: 800; color: #1a1a2e; }
.kpi-value.error-val { color: #dc2626; }
.usage-section { margin-bottom: 24px; }
.usage-section h3 { font-size: 14px; font-weight: 600; color: #374151; margin: 0 0 12px; }
.endpoint-bars { display: flex; flex-direction: column; gap: 8px; }
.endpoint-row { display: flex; align-items: center; gap: 10px; }
.ep-name { font-size: 12px; font-family: monospace; color: #374151; width: 280px; flex-shrink: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ep-bar-wrap { flex: 1; height: 6px; background: #f3f4f6; border-radius: 4px; overflow: hidden; }
.ep-bar { height: 100%; background: #6366F1; border-radius: 4px; transition: width 0.3s; }
.ep-count { font-size: 12px; color: #374151; font-weight: 600; width: 50px; text-align: right; }
.key-usage-list { display: flex; flex-direction: column; gap: 6px; }
.key-usage-row { display: flex; justify-content: space-between; padding: 8px 12px; background: #f9fafb; border-radius: 6px; font-size: 13px; }
.days-select { padding: 6px 12px; border: 1px solid #e5e7eb; border-radius: 6px; font-size: 13px; color: #374151; }

/* Docs */
.docs-content { max-width: 720px; }
.docs-content h2 { font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 0 0 8px; }
.doc-section { margin-top: 28px; }
.doc-section h3 { font-size: 15px; font-weight: 600; color: #374151; margin: 0 0 10px; }
.code-block {
  background: #1e1e2e;
  color: #cdd6f4;
  padding: 16px;
  border-radius: 8px;
  font-size: 13px;
  font-family: monospace;
  overflow-x: auto;
  white-space: pre;
  line-height: 1.6;
}
.events-table { display: flex; flex-direction: column; gap: 0; }
.event-row { display: flex; align-items: center; gap: 16px; padding: 10px 12px; border-bottom: 1px solid #f3f4f6; }
.event-row:first-child { border-top: 1px solid #f3f4f6; }
.event-name { font-family: monospace; font-size: 12px; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; white-space: nowrap; }
.event-desc { font-size: 13px; color: #374151; }
.events-checkboxes { display: flex; flex-direction: column; gap: 8px; max-height: 280px; overflow-y: auto; }

/* Loading & empty */
.loading-state { display: flex; align-items: center; gap: 10px; color: #6b7280; padding: 40px; justify-content: center; }
.spinner { width: 20px; height: 20px; border: 2px solid #e5e7eb; border-top-color: #6366F1; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.empty-state { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 60px 20px; text-align: center; color: #6b7280; }

/* Modal */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}
.modal {
  background: white;
  border-radius: 14px;
  width: 480px;
  max-width: 92vw;
  max-height: 85vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.2);
}
.modal-sm { width: 380px; }
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 24px 0;
}
.modal-header h3 { font-size: 17px; font-weight: 700; color: #1a1a2e; margin: 0; }
.modal-close { background: none; border: none; font-size: 18px; color: #9ca3af; cursor: pointer; padding: 4px; }
.modal-close:hover { color: #374151; }
.modal-body { padding: 16px 24px; }
.modal-footer { padding: 12px 24px 20px; display: flex; justify-content: flex-end; gap: 10px; }

/* Form */
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; font-weight: 600; color: #374151; margin-bottom: 6px; }
.form-input {
  width: 100%; padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  color: #1a1a2e;
  box-sizing: border-box;
}
.form-input:focus { outline: none; border-color: #6366F1; box-shadow: 0 0 0 2px rgba(99,102,241,0.15); }
.scopes-checkboxes { display: flex; gap: 12px; flex-wrap: wrap; }
.scope-check { display: flex; align-items: flex-start; gap: 6px; font-size: 13px; color: #374151; cursor: pointer; }
.form-error { color: #dc2626; font-size: 13px; margin-top: 4px; }

/* New key display */
.new-key-box { background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 10px; padding: 16px; }
.new-key-warning {
  display: flex; align-items: flex-start; gap: 8px;
  background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px;
  padding: 10px 12px; font-size: 13px; color: #92400e;
  margin-bottom: 14px;
}
.new-key-display {
  background: #1e1e2e; border-radius: 8px; padding: 12px 14px;
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
  margin-bottom: 12px;
}
.new-key-display code { color: #cdd6f4; font-family: monospace; font-size: 12px; word-break: break-all; }
.new-key-meta { display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; color: #6b7280; }
.new-key-meta span { background: #f3f4f6; padding: 3px 8px; border-radius: 6px; }

/* Misc */
.dim { color: #9ca3af; font-size: 13px; }
code { font-family: monospace; }
p { margin: 0 0 12px; line-height: 1.6; }

/* MCP Tools */
.mcp-tools-grid { display: flex; flex-direction: column; gap: 16px; }
.mcp-tool-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
  padding: 18px 20px;
}
.mcp-tool-header {
  display: flex; align-items: center; gap: 10px; margin-bottom: 8px;
}
.mcp-tool-name { font-size: 14px; color: #1a1a2e; font-weight: 600; }
.mcp-scope-badge {
  font-size: 11px; padding: 2px 8px; border-radius: 99px;
  background: #e0e7ff; color: #4338ca; font-weight: 600;
}
.mcp-scope-badge.write { background: #fef3c7; color: #92400e; }
.mcp-tool-desc { font-size: 13px; color: #6b7280; margin: 0 0 14px; }
.mcp-tool-section { margin-top: 12px; }
.mcp-param-label { font-size: 11px; font-weight: 700; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 6px; }
.mcp-param-row {
  display: grid; grid-template-columns: 160px 1fr 1fr;
  gap: 8px; font-size: 12px; padding: 4px 0;
  border-bottom: 1px solid #f3f4f6;
  align-items: baseline;
}
.mcp-param-row code { color: #6366F1; }
.mcp-param-row span { color: #6b7280; }
.mcp-param-desc { color: #374151 !important; }
</style>
