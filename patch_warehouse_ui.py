import re

file_path = "frontend/src/pages/Warehouse/WarehouseMasterList.jsx"
with open(file_path, "r") as f:
    content = f.read()

# Add api call method
import_addition = "import { warehouseService } from '../../services/warehouse';\nimport { api } from '../../services/api';"
content = content.replace("import { warehouseService } from '../../services/warehouse';", import_addition)

# Add column
content = content.replace("{ key: 'state', label: 'State' },", "{ key: 'state', label: 'State' },\n    { key: 'amazon_network', label: 'Amazon Network' },")

# Add map logic and dropdown component
map_logic_old = """
      warehouse_type: wh.warehouse_type || '-',
      status: wh.status || 'Active'
    };
  });
"""

map_logic_new = """
      warehouse_type: wh.warehouse_type || '-',
      status: wh.status || 'Active',
      amazon_network: <AmazonNetworkDropdown warehouse={wh} />
    };
  });
"""
content = content.replace(map_logic_old, map_logic_new)

dropdown_component = """
const AmazonNetworkDropdown = ({ warehouse }) => {
  const [network, setNetwork] = useState(
    warehouse.external_mappings?.find(m => m.marketplace === "Amazon")?.amazon_network || ""
  );
  const [saving, setSaving] = useState(false);

  const handleChange = async (e) => {
    const val = e.target.value;
    setNetwork(val);
    setSaving(true);
    try {
      await api.put(`/warehouses/${warehouse.id}/amazon-network`, { amazon_network: val || null });
    } catch (err) {
      alert("Failed to update Amazon network mapping");
    } finally {
      setSaving(false);
    }
  };

  return (
    <select 
      value={network} 
      onChange={handleChange}
      disabled={saving}
      style={{ padding: '0.25rem', borderRadius: '0.25rem', border: '1px solid #ccc' }}
    >
      <option value="">-- None --</option>
      <option value="MFN">MFN</option>
      <option value="AFN">AFN</option>
    </select>
  );
};
"""

content = content.replace("const WarehouseMasterList = () => {", dropdown_component + "\nconst WarehouseMasterList = () => {")

with open(file_path, "w") as f:
    f.write(content)
