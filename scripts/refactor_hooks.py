import os
import re

HOOKS_DIR = 'frontend/src/hooks'

def process_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Add import if not exists
    if 'useCompanyStore' not in content:
        # Find first import
        import_idx = content.find('import')
        if import_idx != -1:
            content = content[:import_idx] + "import useCompanyStore from '../store/useCompanyStore';\n" + content[import_idx:]
        else:
            content = "import useCompanyStore from '../store/useCompanyStore';\n" + content

    # We need to inject `const companyId = useCompanyStore((state) => state.companyId);` into every exported hook.
    # A hook looks like `export const use... = (...) => {`
    
    # regex for hook definition
    hook_pattern = re.compile(r'(export const use\w+\s*=\s*(async\s*)?\([^)]*\)\s*=>\s*\{)')
    
    def repl_hook(match):
        return match.group(1) + "\n  const companyId = useCompanyStore((state) => state.companyId);"
        
    content = hook_pattern.sub(repl_hook, content)
    
    # Now replace queryKeys
    # queryKey: ['something', 'else'] -> queryKey: ['something', 'else', companyId]
    # queryKey: ['something'] -> queryKey: ['something', companyId]
    
    # A simple regex to find queryKey arrays. We have to be careful about nested arrays, but we mostly have simple ones.
    qk_pattern = re.compile(r'queryKey:\s*\[(.*?)\]')
    
    def repl_qk(match):
        inner = match.group(1).strip()
        if not inner:
            return "queryKey: [companyId]"
        if 'companyId' not in inner:
            return f"queryKey: [{inner}, companyId]"
        return match.group(0) # already has it
        
    content = qk_pattern.sub(repl_qk, content)
    
    # queryClient.invalidateQueries({ queryKey: ['products'] }) -> queryClient.invalidateQueries({ queryKey: ['products', companyId] })
    # This is also covered by the qk_pattern above!
    
    # queryClient.setQueryData(['products'] -> queryClient.setQueryData(['products', companyId]
    # queryClient.getQueryData(['products']
    # queryClient.cancelQueries({ queryKey: ['products'] }
    
    qd_pattern = re.compile(r'queryClient\.(setQueryData|getQueryData)\(\[(.*?)\]')
    def repl_qd(match):
        inner = match.group(2).strip()
        if 'companyId' not in inner:
            return f"queryClient.{match.group(1)}([{inner}, companyId]"
        return match.group(0)
    
    content = qd_pattern.sub(repl_qd, content)

    with open(filepath, 'w') as f:
        f.write(content)
        
    print(f"Processed {filepath}")

for filename in os.listdir(HOOKS_DIR):
    if filename.endswith('.js') or filename.endswith('.jsx'):
        process_file(os.path.join(HOOKS_DIR, filename))
