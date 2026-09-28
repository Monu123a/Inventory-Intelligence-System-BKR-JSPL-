import re

file_path = "frontend/src/pages/Warehouse/StateHubsPage.jsx"
with open(file_path, "r") as f:
    content = f.read()

dropdown_component = """
const AmazonNetworkDropdown = ({ warehouse }) => {
  const [network, setNetwork] = React.useState(
    warehouse.external_mappings?.find(m => m.marketplace === "Amazon")?.amazon_network || ""
  );
  const [saving, setSaving] = React.useState(false);

  const handleChange = async (e) => {
    const val = e.target.value;
    setNetwork(val);
    setSaving(true);
    try {
      const { api } = await import('../../services/api');
      await api.default.put(`/warehouses/${warehouse.id}/amazon-network`, { amazon_network: val || null });
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
      style={{ padding: '0.25rem', borderRadius: '0.25rem', border: '1px solid #ccc', marginLeft: '1rem', fontSize: '0.75rem' }}
    >
      <option value="">Amazon: None</option>
      <option value="MFN">Amazon: MFN</option>
      <option value="AFN">Amazon: AFN</option>
    </select>
  );
};
"""

if "AmazonNetworkDropdown" not in content:
    content = content.replace("const StateHubsPage = () => {", dropdown_component + "\nconst StateHubsPage = () => {")

target = "<span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', color: wh.status === 'Active' ? 'green' : 'gray' }}>{wh.status || 'Active'}</span>"
replacement = target + "\n                                <AmazonNetworkDropdown warehouse={wh} />"

if "<AmazonNetworkDropdown warehouse={wh} />" not in content:
    content = content.replace(target, replacement)

with open(file_path, "w") as f:
    f.write(content)
