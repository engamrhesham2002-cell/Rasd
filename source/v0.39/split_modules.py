from pathlib import Path
import ast
root=Path(r'C:\Users\Acer_3aLmy™\Desktop\pg\log\Rasd_v0.31'); p=root/'app.py'; s=p.read_text(encoding='utf-8-sig'); lines=s.splitlines(keepends=True); cls=next(n for n in ast.parse(s).body if isinstance(n,ast.ClassDef) and n.name=='App')
g={'main_ui':[],'files':[],'search':[],'previews':[]}
files={'scan_worker','populate','activate','navigate_to','open_file','selected_path','manage_file_tags','edit_folder_specialties','edit_tags','copy_selected_paths','selected_paths','clear_selected_tags','delete_selected_paths','_finish_delete','context_menu','go_back','go_forward','go_up','rescan'}
previews={'preview_selected','preview_excel_worker','excel_col_name','excel_cell','excel_cell_selected','excel_sheet_changed','load_excel_preview_page','preview_worker','dwg_preview_worker','make_card','_font','_text_image','_table_image','make_file_preview','shell_thumbnail','autocad_core_console_path','short_windows_path','dwg_preview_cache_path','crop_cad_preview','make_autocad_dwg_preview','make_dxf_preview','render_preview','paint_preview','preview_pan_start','preview_pan_move','preview_wheel','zoom_preview','change_pdf_page','hide_excel_preview','render_excel_preview'}
prefixes=('show_search','refresh_search','save_search','load_search','delete_search','search_','launch_everything','start_everything','attach_everything','resize_everything','hide_everything','prepare_everything','everything_','render_search','schedule_search','record_search')
for n in cls.body:
 if isinstance(n,ast.FunctionDef):g['files' if n.name in files else 'previews' if n.name in previews else 'search' if n.name.startswith(prefixes) else 'main_ui'].append(n)
for k,ns in g.items():
 out='class App(tk.Tk):\n'
 for n in ns:out+=''.join(lines[n.lineno-1:n.end_lineno])+'\n'
 (root/f'{k}.py').write_text(out if ns else '',encoding='utf-8')
