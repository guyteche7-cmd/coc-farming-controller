import cv2
import glob

full_screens = [
    r"assets/reference/media_1787426597559.jpg",
    r"assets/reference/media_1787423034404.jpg",
    r"assets/reference/media_1787423139039.png",
    r"assets/reference/media_1787423300906.png",
    r"assets/reference/media_1787423708404.png",
]

for p in full_screens:
    img = cv2.imread(p)
    if img is not None:
        h, w, _ = img.shape
        print(f"File: {p.split('/')[-1]} | Shape: {w}x{h}")
        for tmpl_name in ["home_attack_button", "find_match_battle_button", "army_screen_attack_button", "next_button", "end_battle_active_button", "surrender_button", "return_home_button"]:
            t_path = f"assets/ui/{tmpl_name}.png"
            tmpl = cv2.imread(t_path)
            if tmpl is not None:
                th, tw, _ = tmpl.shape
                res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                if max_val > 0.60:
                    cx = (max_loc[0] + tw // 2) / float(w)
                    cy = (max_loc[1] + th // 2) / float(h)
                    print(f"   Matched {tmpl_name:25s} score={max_val:.3f} center=({cx:.3f}, {cy:.3f})")
