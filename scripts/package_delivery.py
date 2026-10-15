"""Package tracked files and actual Git history; never include credentials."""
from pathlib import Path
import subprocess,zipfile,hashlib
root=Path(__file__).resolve().parents[1]
out=root.parent/'outputs';out.mkdir(exist_ok=True)
bundle=out/'FerreMax_U3_Historial.bundle'
subprocess.run(['git','bundle','create',str(bundle),'--all'],cwd=root,check=True)
files=[s for s in subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0') if s]
with zipfile.ZipFile(out/'FerreMax_U3_Paquete.zip','w',zipfile.ZIP_DEFLATED) as z:
    hashes=[]
    for f in files:
        p=root/f;z.write(p,'FerreMax_U3/'+f);hashes.append(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+f)
    z.write(bundle,'FerreMax_U3/'+bundle.name)
    z.writestr('FerreMax_U3/HISTORIAL_GIT.txt','Tres commits locales preparados por IA. Restaurar el historial en otra carpeta:\ngit clone FerreMax_U3_Historial.bundle ferremax-con-historial\n\nLa publicación en GitHub sigue pendiente. No se han creado revisiones humanas ni commits atribuidos a los integrantes.\n')
    z.writestr('FerreMax_U3/SHA256SUMS.txt','\n'.join(hashes)+'\n')
with zipfile.ZipFile(out/'FerreMax_U3_Paquete.zip') as z:
    assert z.testzip() is None
    print('Paquete validado:',len(z.namelist()),'archivos')
