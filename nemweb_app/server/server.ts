import { createApp, analytics, lakebase, server } from '@databricks/appkit';
import { z } from 'zod';
import {
  createInvestigation,
  deleteInvestigation,
  listInvestigations,
  migrateInvestigations,
  trustedOperatorIdentity,
  updateInvestigation,
} from './db/investigations';

const investigationIdSchema = z.string().uuid();
const logDatabaseError = (operation: string, error: unknown) => {
  console.error(`${operation} failed`, error);
};

async function start() {
  await createApp({
    plugins: [analytics(), lakebase(), server()],
    async onPluginsReady(appkit) {
      await migrateInvestigations(appkit.lakebase);

      appkit.server.extend((app) => {
        app.get('/api/region-status', async (_req, res) => {
          try {
            const result = await appkit.lakebase.query(
              `SELECT * FROM app_read.nem_region_status_synced
               ORDER BY interval_end DESC, region_id
               LIMIT 100`
            );
            res.json(result.rows);
          } catch (error) {
            logDatabaseError('Synced region status read', error);
            res.status(500).json({ error: 'Synced region status read failed' });
          }
        });

        app.get('/api/investigations', async (req, res) => {
          try {
            const operator = trustedOperatorIdentity(req.headers);
            res.json(await listInvestigations(appkit.lakebase, operator));
          } catch (error) {
            logDatabaseError('Investigation read', error);
            res.status(500).json({ error: 'Investigation read failed' });
          }
        });

        app.post('/api/investigations', async (req, res) => {
          try {
            const operator = trustedOperatorIdentity(req.headers);
            res.status(201).json(await createInvestigation(appkit.lakebase, req.body, operator));
          } catch (error) {
            const identityFailure = error instanceof Error && error.message.includes('AppKit');
            if (!identityFailure) logDatabaseError('Investigation create', error);
            res.status(identityFailure ? 401 : 400).json({
              error: identityFailure ? 'Trusted application identity is unavailable' : 'Invalid investigation',
            });
          }
        });

        app.patch('/api/investigations/:id', async (req, res) => {
          try {
            const operator = trustedOperatorIdentity(req.headers);
            if (!investigationIdSchema.safeParse(req.params.id).success) {
              res.status(400).json({ error: 'Invalid investigation id' });
              return;
            }
            const parsed = req.body as {
              expectedVersion?: number;
              status?: string;
              decision?: string;
            };
            if (
              !Number.isInteger(parsed.expectedVersion) ||
              !['open', 'reviewing', 'closed'].includes(parsed.status ?? '') ||
              typeof parsed.decision !== 'string'
            ) {
              res.status(400).json({ error: 'expectedVersion, status, and decision are required' });
              return;
            }
            const row = await updateInvestigation(
              appkit.lakebase,
              req.params.id,
              parsed.expectedVersion!,
              parsed.status as 'open' | 'reviewing' | 'closed',
              parsed.decision,
              operator
            );
            if (!row) {
              res.status(404).json({ error: 'Investigation not found or version conflict' });
              return;
            }
            res.json(row);
          } catch (error) {
            logDatabaseError('Investigation update', error);
            res.status(500).json({ error: 'Investigation update failed' });
          }
        });

        app.delete('/api/investigations/:id', async (req, res) => {
          try {
            const operator = trustedOperatorIdentity(req.headers);
            if (!investigationIdSchema.safeParse(req.params.id).success) {
              res.status(400).json({ error: 'Invalid investigation id' });
              return;
            }
            const deleted = await deleteInvestigation(appkit.lakebase, req.params.id, operator);
            if (!deleted) {
              res.status(404).json({ error: 'Investigation not found' });
              return;
            }
            res.status(204).send();
          } catch (error) {
            logDatabaseError('Investigation delete', error);
            res.status(500).json({ error: 'Investigation delete failed' });
          }
        });
      });
    },
  });
}

start().catch(console.error);
