from pathlib import Path
import ast

root = Path(__file__).resolve().parent
source = root / 'full code' / 'app.py'
text = source.read_text(encoding='utf-8-sig')
lines = text.splitlines(keepends=True)
app_class = next(node for node in ast.parse(text).body if isinstance(node, ast.ClassDef) and node.name == 'App')

groups = {'main_ui': [], 'files': [], 'search': [], 'previews': []}
file_methods = {'scan_worker','populate','activate','navigate_to','open_file','selected_path','manage_file_tags','edit_folder_specialties','edit_tags','copy_selected_paths','selected_paths','clear_selected_tags','delete_selected_paths','_finish_delete','context_menu','go_back','go_forward','go_up','rescan'}
preview_methods = {'preview_selected','preview_excel_worker','excel_col_name','excel_cell','excel_cell_selected','excel_sheet_changed','load_excel_preview_page','preview_worker','dwg_preview_worker','make_card','_font','_text_image','_table_image','make_file_preview','shell_thumbnail','autocad_core_console_path','short_windows_path','dwg_preview_cache_path','crop_cad_preview','make_autocad_dwg_preview','make_dxf_preview','render_preview','paint_preview','preview_pan_start','preview_pan_move','preview_wheel','zoom_preview','change_pdf_page','hide_excel_preview','render_excel_preview'}
search_prefixes = ('show_search','refresh_search','save_search','load_search','delete_search','search_','launch_everything','start_everything','attach_everything','resize_everything','hide_everything','prepare_everything','everything_','render_search','schedule_search','record_search')
for node in app_class.body:
    if not isinstance(node, ast.FunctionDef):
        continue
    group = 'files' if node.name in file_methods else 'previews' if node.name in preview_methods else 'search' if node.name.startswith(search_prefixes) else 'main_ui'
    groups[group].append(node)

for name, nodes in groups.items():
    output = 'class App(tk.Tk):\n'
    for node in nodes:
        output += ''.join(lines[node.lineno - 1:node.end_lineno]) + '\n'
    (root / f'{name}.py').write_text(output, encoding='utf-8')
