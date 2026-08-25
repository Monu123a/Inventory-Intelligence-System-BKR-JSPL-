import re

with open('frontend/src/pages/WarehouseLogistics/BatchDispatchCreator.jsx', 'r') as f:
    content = f.read()

dropdown = """
                <div style={{ marginTop: '2rem', padding: '1.5rem', backgroundColor: '#f9fafb', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                  <h4 style={{ margin: '0 0 1rem 0', color: '#374151', fontSize: '0.95rem' }}>Or select a specific source warehouse:</h4>
                  <select 
                    className={styles.inputField}
                    value={sourceWarehouseId || ''}
                    onChange={(e) => setSourceWarehouseId(parseInt(e.target.value, 10))}
                  >
                    <option value="">-- Select Source Warehouse --</option>
                    {warehouses.map(w => (
                      <option key={w.id} value={w.id}>{w.name} ({w.code})</option>
                    ))}
                  </select>
                </div>
              </div>
"""

content = content.replace('              </div>\n              <div className={styles.actionRow}>\n                <button \n                  className={styles.btnPrimary}', dropdown + '              <div className={styles.actionRow}>\n                <button \n                  className={styles.btnPrimary}')

with open('frontend/src/pages/WarehouseLogistics/BatchDispatchCreator.jsx', 'w') as f:
    f.write(content)
