import re

with open('frontend/src/pages/Settings/SettingsPage.jsx', 'r') as f:
    content = f.read()

# Add import
content = content.replace("import { FiSave, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';", "import { FiSave, FiAlertCircle, FiCheckCircle } from 'react-icons/fi';\nimport { useQueryClient } from '@tanstack/react-query';")

# Add queryClient hook
content = content.replace("const [message, setMessage] = useState({ text: '', type: '' });", "const [message, setMessage] = useState({ text: '', type: '' });\n  const queryClient = useQueryClient();")

# Add invalidateQueries
content = content.replace("await api.put('/api/settings/', settings);", "await api.put('/api/settings/', settings);\n      queryClient.invalidateQueries({ queryKey: ['companies'] });")

with open('frontend/src/pages/Settings/SettingsPage.jsx', 'w') as f:
    f.write(content)

