import os

def get_directory_tree(path, no_descend_dirs, exclude_dirs={".git", "__pycache__"}, 
                       exclude_files=set(), exclude_ext=set(), prefix=""):
    tree_str = ""
    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return ""
    # Filtrage : on exclut les dossiers et fichiers spécifiés dans les listes correspondantes
    visible_entries = []
    for entry in entries:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            if entry in exclude_dirs:
                continue
        elif os.path.isfile(full_path):
            if entry in exclude_files:
                continue
            # Exclure les fichiers dont l'extension figure dans exclude_ext
            if any(entry.endswith(ext) for ext in exclude_ext):
                continue
        visible_entries.append(entry)
        
    for i, entry in enumerate(visible_entries):
        full_path = os.path.join(path, entry)
        connector = "└── " if i == len(visible_entries) - 1 else "├── "
        tree_str += prefix + connector + entry + "\n"
        if os.path.isdir(full_path):
            if entry in no_descend_dirs:
                # Affiche uniquement les fichiers contenus directement dans ce dossier, sans explorer les sous-dossiers,
                # en filtrant également les fichiers exclus par nom ou par extension.
                try:
                    sub_entries = sorted(os.listdir(full_path))
                except PermissionError:
                    sub_entries = []
                file_entries = [
                    e for e in sub_entries
                    if os.path.isfile(os.path.join(full_path, e))
                    and e not in exclude_files
                    and not any(e.endswith(ext) for ext in exclude_ext)
                ]
                for j, file_entry in enumerate(file_entries):
                    sub_connector = "└── " if j == len(file_entries) - 1 else "├── "
                    tree_str += prefix + ("    " if i == len(visible_entries) - 1 else "│   ") + sub_connector + file_entry + "\n"
            else:
                sub_prefix = prefix + ("    " if i == len(visible_entries) - 1 else "│   ")
                tree_str += get_directory_tree(full_path, no_descend_dirs, exclude_dirs, exclude_files, exclude_ext, sub_prefix)
    return tree_str

def extract_python_code(directory, output_file, no_descend_dirs, exclude_dirs={".git"}, 
                        exclude_files=set(), exclude_ext=set()):
    with open(output_file, 'w', encoding='utf-8') as output:
        # Génère et écrit l'arborescence du projet
        root_name = os.path.basename(directory)
        tree = root_name + "\n" + get_directory_tree(directory, no_descend_dirs, exclude_dirs, exclude_files, exclude_ext)
        output.write(tree)
        output.write("\n" + "=" * 80 + "\n")
        
        # Parcourt récursivement le dossier et ses sous-dossiers pour extraire et afficher le contenu de tous les fichiers,
        # en excluant les dossiers et fichiers spécifiés (par nom et par extension).
        for root, dirs, files in os.walk(directory):
            # Exclure les dossiers définis dans exclude_dirs
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            # Si le dossier courant est dans no_descend_dirs, n'explore pas plus loin son contenu.
            if os.path.basename(root) in no_descend_dirs:
                dirs[:] = []
            for file in files:
                if file in exclude_files or any(file.endswith(ext) for ext in exclude_ext):
                    continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, directory)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    content = f"Erreur de lecture: {e}"
                output.write(f"Chemin relatif: {relative_path}\n")
                output.write(content)
                output.write("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    # Détermine le dossier racine du projet (par défaut, le dossier parent du répertoire contenant ce script)
    directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # Spécifie le fichier de sortie
    output_file = os.path.join(directory, 'docs', 'source.txt')
    
    # Liste des dossiers dans lesquels on ne descend pas (par exemple, aucun ici ou ceux que vous souhaitez limiter)
    no_descend_dirs = []
    
    # Liste des dossiers à exclure complètement : ici, on exclut "env", "test", ".git" et "__pycache__"
    exclude_dirs = {"env", ".git", "__pycache__", "test"}
    
    # Liste des fichiers à exclure : ici, on ignore "source.py" et "source.txt"
    exclude_files = {"source.py", "source.txt", ".gitignore" }
    
    # Liste des extensions à exclure : par exemple, on peut exclure les fichiers ".drawio"
    exclude_ext = {".drawio"}
    
    extract_python_code(directory, output_file, no_descend_dirs, exclude_dirs, exclude_files, exclude_ext)

