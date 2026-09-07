import { describe, expect, it } from 'vitest';
import {
  createInvestigation,
  deleteInvestigation,
  trustedOperatorIdentity,
  updateInvestigation,
  type LakebaseQuery,
} from './investigations';

class FakeDatabase implements LakebaseQuery {
  calls: { text: string; params?: unknown[] }[] = [];
  rows: Record<string, unknown>[] = [{ investigation_id: 'id-1', version: 1 }];

  query(text: string, params?: unknown[]) {
    this.calls.push({ text, params });
    return Promise.resolve({ rows: this.rows });
  }
}

const input = {
  nemEventKey: 'NSW1|2026-07-01T00:05:00+10:00',
  regionId: 'NSW1',
  intervalEnd: '2026-07-01T00:05:00+10:00',
  teamIdentifier: 'pair-1',
  status: 'open' as const,
  decision: 'Inspect',
  evidenceReference: 'fixture://1',
};

function firstCall(database: FakeDatabase) {
  const call = database.calls[0];
  if (!call) throw new Error('expected a database call');
  return call;
}

describe('investigation database contract', () => {
  it('uses trusted forwarded identity and ignores any client identity field', async () => {
    expect(
      trustedOperatorIdentity({ 'x-forwarded-user': 'operator@example.invalid' }, 'agentic-energy-workshop-d4')
    ).toBe('operator@example.invalid');
    expect(() => trustedOperatorIdentity({}, 'agentic-energy-workshop-d4')).toThrow(/identity/);
    expect(() => trustedOperatorIdentity({ 'x-forwarded-user': 'forged@example.invalid' }, '')).toThrow(
      /proxy context/
    );
    const database = new FakeDatabase();
    await createInvestigation(database, { ...input, operatorIdentity: 'attacker' }, 'trusted@example.invalid');
    expect(firstCall(database).params).toContain('trusted@example.invalid');
    expect(firstCall(database).params).not.toContain('attacker');
  });

  it('parameterises inserts, optimistic updates, and deletes', async () => {
    const database = new FakeDatabase();
    await createInvestigation(database, input, 'operator@example.invalid');
    expect(firstCall(database).text).toContain('VALUES ($1, $2, $3, $4, $5, $6, $7, $8)');
    expect(firstCall(database).text).not.toContain(input.decision);

    await updateInvestigation(
      database,
      '11111111-1111-4111-8111-111111111111',
      1,
      'closed',
      'Done',
      'operator@example.invalid'
    );
    const updateCall = database.calls[1];
    if (!updateCall) throw new Error('expected update call');
    expect(updateCall.text).toContain('version = version + 1');
    expect(updateCall.text).toContain('version = $4 AND operator_identity = $5');

    await deleteInvestigation(database, '11111111-1111-4111-8111-111111111111', 'operator@example.invalid');
    const deleteCall = database.calls[2];
    if (!deleteCall) throw new Error('expected delete call');
    expect(deleteCall.text).toContain('investigation_id = $1::uuid');
    expect(deleteCall.text).toContain('operator_identity = $2');
  });

  it('rejects malformed input and reports not-found/version conflict as null', async () => {
    const database = new FakeDatabase();
    await expect(createInvestigation(database, { ...input, regionId: 'bad' }, 'trusted')).rejects.toThrow();
    database.rows = [];
    await expect(
      updateInvestigation(database, '11111111-1111-4111-8111-111111111111', 99, 'closed', 'Done', 'trusted')
    ).resolves.toBeNull();
    await expect(deleteInvestigation(database, '11111111-1111-4111-8111-111111111111', 'trusted')).resolves.toBe(false);
  });
});
