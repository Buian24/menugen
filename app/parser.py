import pandas as pd
import os

REQUIRED_COLUMNS = ['ten_mon', 'gia', 'nhom']

def parse_excel(filepath: str) -> dict:
    """
    Đọc file Excel, trả về dict chứa thông tin menu.
    Cột bắt buộc: ten_mon, gia, nhom
    Cột tùy chọn: mo_ta, ghi_chu
    """
    try:
        df = pd.read_excel(filepath, engine='openpyxl')
        df.columns = [col.strip().lower().replace(' ', '_') for col in df.columns]

        # Kiểm tra cột bắt buộc
        missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
        if missing:
            return {
                'success': False,
                'error': f'File thiếu các cột: {", ".join(missing)}. '
                         f'Xem file mẫu để biết đúng format.'
            }

        df = df.dropna(subset=['ten_mon', 'gia'])
        df['gia'] = pd.to_numeric(df['gia'], errors='coerce').fillna(0).astype(int)
        df['mo_ta'] = df.get('mo_ta', '').fillna('')
        df['ghi_chu'] = df.get('ghi_chu', '').fillna('')

        # Nhóm món
        groups = {}
        for _, row in df.iterrows():
            nhom = str(row.get('nhom', 'Món chính')).strip()
            if nhom not in groups:
                groups[nhom] = []
            groups[nhom].append({
                'ten': str(row['ten_mon']).strip(),
                'gia': int(row['gia']),
                'mo_ta': str(row['mo_ta']).strip(),
                'ghi_chu': str(row['ghi_chu']).strip(),
            })

        return {
            'success': True,
            'groups': groups,
            'total_items': len(df),
        }

    except Exception as e:
        return {'success': False, 'error': f'Lỗi đọc file: {str(e)}'}
