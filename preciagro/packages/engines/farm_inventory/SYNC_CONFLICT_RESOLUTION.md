# Offline-First Sync Conflict Resolution

## Overview

The Farm Inventory Engine supports offline-first operation with conflict resolution when syncing with the central server.

## Sync Architecture

- **Local Storage**: SQLite (offline usage)
- **Server Storage**: PostgreSQL (authoritative)
- **Sync State**: Tracks pending operations and conflicts

## Conflict Resolution Rules

### 1. Server is Authoritative

**Rule**: Server state always wins in conflicts.

When a conflict is detected:
1. Server state is preserved
2. Local conflicting change is logged in `SyncState.conflict_data`
3. Conflict is marked as unresolved
4. Admin/farmer is notified

### 2. Conflict Types

#### A. Quantity Conflicts
**Scenario**: Local deducted 10kg, server deducted 5kg for same item.

**Resolution**:
- Server quantity is authoritative
- Local deduction is logged as conflict
- If local deduction would cause negative inventory, it's rejected
- If both are valid, server quantity is used, local deduction is applied as adjustment

#### B. Concurrent Updates
**Scenario**: Local updated item name, server updated item quantity.

**Resolution**:
- Server quantity wins
- Local name update is merged if no server name update exists
- If both updated same field, server wins

#### C. Deletion Conflicts
**Scenario**: Local deleted item, server updated item.

**Resolution**:
- Server update wins (item is not deleted)
- Local deletion is logged as conflict
- Item is restored from server state

### 3. Local Negative Inventory (Temporary)

**Rule**: Local negative inventory is allowed temporarily during offline usage.

**Rationale**:
- Farmer may use inventory offline
- Sync will reconcile when connectivity is restored
- Server will prevent negative inventory

**Reconciliation**:
- When syncing, if local quantity is negative:
  - Server quantity is used (authoritative)
  - Negative usage is logged as conflict
  - Alert is generated for farmer

### 4. Conflict Logging

All conflicts are logged in `SyncState` table:

```json
{
  "conflict_type": "quantity_mismatch",
  "local_value": 10.5,
  "server_value": 15.0,
  "resolution": "server_wins",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 5. Conflict Notification

Conflicts are exposed via:
- Admin dashboard
- API endpoint: `GET /inventory/sync/conflicts`
- Alert system (for critical conflicts)

## Sync Process

### Step 1: Upload Local Changes
1. Query `SyncState` for unsynced operations
2. Upload to server
3. Server validates and applies

### Step 2: Detect Conflicts
1. Server compares local state with server state
2. Identifies conflicts
3. Marks conflicts in `SyncState`

### Step 3: Resolve Conflicts
1. Server state is applied (authoritative)
2. Conflicts are logged
3. Local state is updated to match server

### Step 4: Download Server Changes
1. Download server changes since last sync
2. Apply to local database
3. Update sync timestamps

## Implementation Status

**Current**: Schema and models ready
**Next**: Implement sync service with conflict resolution logic

## Example Conflict Resolution

```python
# Local state (offline)
item.quantity = 5.0  # Farmer used 10kg offline

# Server state (authoritative)
item.quantity = 15.0  # Server shows 15kg

# Resolution
conflict = {
    "type": "quantity_mismatch",
    "local": 5.0,
    "server": 15.0,
    "resolution": "server_wins",
    "local_deduction_logged": True
}

# Final state
item.quantity = 15.0  # Server wins
# Local usage log is preserved but flagged
```

## Best Practices

1. **Sync Frequently**: Sync every 5 minutes when online
2. **Validate Before Sync**: Check for obvious conflicts before uploading
3. **Notify on Conflicts**: Always notify farmer/admin of conflicts
4. **Preserve Audit Trail**: Never delete usage logs, even in conflicts
5. **Server Validation**: Server must validate all operations before applying

