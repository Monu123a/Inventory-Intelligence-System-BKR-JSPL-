import { transformSync } from 'esbuild';
import fs from 'fs';

const code = fs.readFileSync('src/pages/Service/CreateServicePage.jsx', 'utf-8');

try {
  transformSync(code, { loader: 'jsx' });
  console.log('Syntax OK');
} catch (e) {
  console.error('Syntax Error:', e.message);
}
