# NEM regional operations app

React/Node with AppKit Lakebase and server plugins. Deployment is owned by the repository-root bundle.

```sh
npm ci --ignore-scripts --legacy-peer-deps
npm run typecheck
npm run lint
npm test
npm run build
npm run test:smoke
```

The default client reads `/api/region-status`, `/api/fuel-generation`, and `/api/unit-dispatch`. Each endpoint uses a fixed bounded Lakebase query. Fuel and unit failures affect their own panels. Native investigation routes use app-owned `app_write` tables, trusted identity, and optimistic concurrency.

Use `VITE_DATA_MODE=mock npm run build:client` for a non-live fixture preview. The browser suite exercises prepared data and mocked writes; it does not validate deployed Lakebase connectivity. Deploy the app before authenticated local development so its service principal owns the investigation schema.

See [operations](../docs/operations.md) for publication, sync verification, grants, and app deployment.
