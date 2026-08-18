const fs = require('fs');
const babel = require('@babel/core');

const code = fs.readFileSync('src/pages/Service/CreateServicePage.jsx', 'utf-8');

try {
  babel.transformSync(code, {
    presets: ['@babel/preset-react'],
    filename: 'CreateServicePage.jsx'
  });
  console.log('Syntax OK');
} catch (e) {
  console.error('Syntax Error:', e.message);
}
