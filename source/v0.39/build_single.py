from pathlib import Path
import ast
root=Path(__file__).resolve().parent
prefix=(root/'core.py').read_text(encoding='utf-8-sig').rstrip()+chr(10)*2
body=[]
for name in ['main_ui.py','files.py','search.py','previews.py']:
 text=(root/name).read_text(encoding='utf-8-sig').strip()
 if not text: continue
 lines=text.splitlines(keepends=True)
 if not lines[0].startswith('class App(tk.Tk):'): raise RuntimeError(f'Invalid class module: {name}')
 body.append(''.join(lines[1:]).rstrip()+chr(10))
merged=prefix+'class App(tk.Tk):'+chr(10)+''.join(body)+chr(10)+"if __name__ == '__main__':"+chr(10)+' if not launch_pending_update_at_start(): App().mainloop()'+chr(10)
t=ast.parse(merged)
if sum(isinstance(n,ast.ClassDef) and n.name=='App' for n in t.body)!=1: raise RuntimeError('Expected one App class')
target=root/'full code'/'app.py';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged,encoding='utf-8')
print(f'Generated {target} ({len(merged):,} characters)')
