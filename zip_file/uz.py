import zipfile
import os
import shutil

zip_folder = r'C:\Users\user\Documents\_08_holdwin_data\_01_web\zip_file'
output_folder = r'C:\Users\user\Documents\_08_holdwin_data\_01_web\data'

os.makedirs(output_folder, exist_ok=True)

zip_files = [
 
'drive-download-20251208T055928Z-1-001.zip'
]

for zip_name in zip_files:
    zip_path = os.path.join(zip_folder, zip_name)
    
    if os.path.exists(zip_path):
        print(f'解壓縮: {zip_name}')
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                filename = os.path.basename(member)
                
                if not filename:
                    continue
                
                source = zip_ref.open(member)
                target_path = os.path.join(output_folder, filename)
                
                with open(target_path, 'wb') as target:
                    shutil.copyfileobj(source, target)
                source.close()
        
        os.remove(zip_path)
        print(f'已刪除: {zip_name}')
    else:
        print(f'找不到: {zip_name}')

print('\n完成!')