import { z } from 'zod';
import { INVESTIGATIONS_MIGRATION } from './schema';

export interface LakebaseQuery {
  query(text: string, params?: unknown[]): Promise<{ rows: Record<string, unknown>[] }>;
}

export const InvestigationInput = z.object({
  nemEventKey: z.string().min(1).max(300),
  regionId: z.string().regex(/^[A-Z]{2,4}1$/),
  intervalEnd: z.string().datetime({ offset: true }),
  teamIdentifier: z.string().min(1).max(100),
  status: z.enum(['open', 'reviewing', 'closed']),
  decision: z.string().max(5000),
  evidenceReference: z.string().max(1000).nullable().optional(),
});

export function trustedOperatorIdentity(
  headers: Record<string, string | string[] | undefined>,
  runtimeAppName = process.env.DATABRICKS_APP_NAME
): string {
  if (!runtimeAppName?.trim()) {
    throw new Error('Trusted AppKit proxy context is unavailable');
  }
  const header = headers['x-forwarded-user'];
  const value = Array.isArray(header) ? header[0] : header;
  if (!value?.trim()) throw new Error('Trusted AppKit operator identity is unavailable');
  return value.trim();
}

export async function migrateInvestigations(database: LakebaseQuery): Promise<void> {
  await database.query(INVESTIGATIONS_MIGRATION);
}

export async function createInvestigation(
  database: LakebaseQuery,
  body: unknown,
  operatorIdentity: string
): Promise<Record<string, unknown>> {
  const input = InvestigationInput.parse(body);
  const result = await database.query(
    `INSERT INTO app_write.investigations
      (nem_event_key, region_id, interval_end, operator_identity, team_identifier,
       status, decision, evidence_reference)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
     RETURNING *`,
    [
      input.nemEventKey,
      input.regionId,
      input.intervalEnd,
      operatorIdentity,
      input.teamIdentifier,
      input.status,
      input.decision,
      input.evidenceReference ?? null,
    ]
  );
  const row = result.rows[0];
  if (!row) throw new Error('Lakebase did not return the created investigation');
  return row;
}

export async function listInvestigations(
  database: LakebaseQuery,
  operatorIdentity: string
): Promise<Record<string, unknown>[]> {
  const result = await database.query(
    `SELECT * FROM app_write.investigations
     WHERE operator_identity = $1 ORDER BY updated_at DESC, investigation_id`,
    [operatorIdentity]
  );
  return result.rows;
}

export async function updateInvestigation(
  database: LakebaseQuery,
  investigationId: string,
  expectedVersion: number,
  status: 'open' | 'reviewing' | 'closed',
  decision: string,
  operatorIdentity: string
): Promise<Record<string, unknown> | null> {
  const result = await database.query(
    `UPDATE app_write.investigations
     SET status = $1, decision = $2, updated_at = NOW(), version = version + 1
     WHERE investigation_id = $3::uuid AND version = $4 AND operator_identity = $5
     RETURNING *`,
    [status, decision, investigationId, expectedVersion, operatorIdentity]
  );
  return result.rows[0] ?? null;
}

export async function deleteInvestigation(
  database: LakebaseQuery,
  investigationId: string,
  operatorIdentity: string
): Promise<boolean> {
  const result = await database.query(
    `DELETE FROM app_write.investigations
     WHERE investigation_id = $1::uuid AND operator_identity = $2
     RETURNING investigation_id`,
    [investigationId, operatorIdentity]
  );
  return result.rows.length === 1;
}
