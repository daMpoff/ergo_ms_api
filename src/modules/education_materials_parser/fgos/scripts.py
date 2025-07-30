import os
import re
import time
import requests

from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from datetime import datetime

from django.conf import settings
from django.utils import timezone

from src.modules.education_materials_parser.fgos.models import FgosDocument, FgosParsingSession


class FgosParser:
    """Парсер для сбора документов ФГОС с сайта fgos.ru"""
    
    def __init__(self):
        self.base_url = "https://fgos.ru"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Создаем папку для файлов, если её нет
        self.media_path = os.path.join(settings.MEDIA_ROOT, 'education_materials_parser')
        os.makedirs(self.media_path, exist_ok=True)
        
        # Текущая сессия парсинга
        self.parsing_session = None
    
    def start_parsing_session(self):
        """Начать новую сессию парсинга"""
        self.parsing_session = FgosParsingSession.objects.create()
        return self.parsing_session
    
    def get_page_content(self, url, timeout=30):
        """Получить содержимое страницы"""
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.RequestException as e:
            print(f"Ошибка при получении страницы {url}: {e}")
            return None
    
    def find_fgos_links(self):
        """Найти все ссылки на страницы ФГОС"""
        fgos_links = set()  # Используем set для избежания дубликатов
        
        print("Поиск ссылок на ФГОС...")
        
        # Стратегия 1: Проверяем основную страницу ФГОС
        main_sections = [
            "/fgos/",
            "",  # Главная страница
        ]
        
        for section in main_sections:
            try:
                section_url = urljoin(self.base_url, section)
                print(f"Сканирование раздела: {section_url}")
                content = self.get_page_content(section_url)
                
                if content:
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # Ищем все ссылки на конкретные ФГОС
                    links = soup.find_all('a', href=True)
                    section_links = 0
                    
                    for link in links:
                        href = link.get('href')
                        if href and '/fgos/fgos-' in href:
                            full_url = urljoin(self.base_url, href)
                            if full_url not in fgos_links:
                                fgos_links.add(full_url)
                                section_links += 1
                    
                    print(f"  Найдено {section_links} ссылок в разделе")
                    
                time.sleep(1)  # Задержка между запросами
                
            except Exception as e:
                print(f"Ошибка при сканировании раздела {section}: {e}")
                continue
        
        # Стратегия 2: Попробуем найти ссылки через карту сайта или навигацию
        try:
            sitemap_urls = [
                "/sitemap.xml",
                "/sitemap",
                "/map"
            ]
            
            for sitemap_url in sitemap_urls:
                try:
                    full_sitemap_url = urljoin(self.base_url, sitemap_url)
                    content = self.get_page_content(full_sitemap_url)
                    
                    if content:
                        # Ищем ссылки на ФГОС в XML или HTML
                        import re
                        fgos_pattern = r'https?://[^\s<>"\']*?/fgos/fgos-[^\s<>"\']*'
                        found_urls = re.findall(fgos_pattern, content)
                        
                        for url in found_urls:
                            if url not in fgos_links:
                                fgos_links.add(url)
                        
                        if found_urls:
                            print(f"  Найдено {len(found_urls)} ссылок в {sitemap_url}")
                            break
                            
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"Ошибка при поиске через карту сайта: {e}")
        
        # Стратегия 3: Прямой поиск по известным кодам специальностей
        # Попробуем сгенерировать возможные URL на основе известных паттернов
        education_codes = [
            # Психологические науки
            "37.05.02", "37.03.01", "37.04.01",
            # Педагогические науки  
            "44.03.01", "44.03.02", "44.03.03", "44.03.04", "44.03.05",
            "44.04.01", "44.04.02", "44.04.03",
            # Экономические науки
            "38.03.01", "38.03.02", "38.03.03", "38.03.04", "38.03.05",
            "38.04.01", "38.04.02", "38.04.08",
            # Юридические науки
            "40.03.01", "40.04.01", "40.05.01", "40.05.02", "40.05.03",
            # Медицинские науки
            "31.05.01", "31.05.02", "31.05.03",
            # Технические науки (выборочно)
            "09.03.01", "09.03.02", "09.03.03", "09.03.04",
            "09.04.01", "09.04.02", "09.04.03",
        ]
        
        print("Проверка прямых ссылок по кодам специальностей...")
        direct_found = 0
        
        for code in education_codes:
            try:
                # Преобразуем код в формат URL (точки в дефисы)
                url_code = code.replace('.', '-')
                
                # Возможные варианты URL
                possible_urls = [
                    f"/fgos/fgos-{url_code}-",
                    f"/fgos/fgos-{url_code}-uroven-bakalavriata",
                    f"/fgos/fgos-{url_code}-uroven-magistratury", 
                    f"/fgos/fgos-{url_code}-uroven-specialiteta",
                ]
                
                for url_pattern in possible_urls:
                    # Попробуем найти страницы, которые начинаются с этого паттерна
                    search_url = urljoin(self.base_url, url_pattern)
                    
                    # Проверим, есть ли такая страница
                    try:
                        response = self.session.head(search_url, timeout=10)
                        if response.status_code == 200:
                            fgos_links.add(search_url)
                            direct_found += 1
                            print(f"  Найдена прямая ссылка: {search_url}")
                    except:
                        pass
                
                time.sleep(0.5)  # Небольшая задержка
                
            except Exception as e:
                continue
        
        if direct_found > 0:
            print(f"Найдено {direct_found} прямых ссылок")
        
        # Преобразуем set обратно в list
        fgos_links = list(fgos_links)
        
        print(f"Всего найдено {len(fgos_links)} уникальных ссылок на ФГОС")
        
        # Если ничего не найдено, попробуем базовые тестовые ссылки
        if not fgos_links:
            print("Не найдено ссылок, добавляем тестовые...")
            test_links = [
                "https://fgos.ru/fgos/fgos-37-05-02-psihologiya-sluzhebnoy-deyatelnosti-uroven-specialiteta-1613/",
                "https://fgos.ru/fgos/fgos-44-03-01-pedagogicheskoe-obrazovanie-uroven-bakalavriata-121/",
                "https://fgos.ru/fgos/fgos-38-03-01-ekonomika-uroven-bakalavriata-747/",
            ]
            
            for test_link in test_links:
                try:
                    response = self.session.head(test_link, timeout=10)
                    if response.status_code == 200:
                        fgos_links.append(test_link)
                        print(f"  Добавлена тестовая ссылка: {test_link}")
                except:
                    pass
        
        if self.parsing_session:
            self.parsing_session.total_pages_found = len(fgos_links)
            self.parsing_session.save()
        
        return fgos_links
    
    def parse_fgos_page(self, url):
        """Парсить страницу конкретного ФГОС"""
        content = self.get_page_content(url)
        if not content:
            return None
        
        soup = BeautifulSoup(content, 'html.parser')
        
        try:
            # Извлекаем основную информацию
            title = self.extract_title(soup)
            code = self.extract_code(title, url)
            level = self.extract_level(title)
            field_of_study = self.extract_field_of_study(title)
            
            # Ищем ссылку на скачивание PDF
            download_link = self.find_download_link(soup)
            if not download_link:
                print(f"Не найдена ссылка для скачивания на странице {url}")
                return None
            
            download_url = urljoin(self.base_url, download_link)
            
            # Извлекаем дополнительную информацию
            order_number = self.extract_order_number(soup)
            ministry = self.extract_ministry(soup)
            registration_number = self.extract_registration_number(soup)
            published_date = self.extract_published_date(soup)
            
            return {
                'title': title,
                'code': code,
                'level': level,
                'field_of_study': field_of_study,
                'source_url': url,
                'download_url': download_url,
                'order_number': order_number,
                'ministry': ministry,
                'registration_number': registration_number,
                'published_date': published_date,
            }
            
        except Exception as e:
            print(f"Ошибка при парсинге страницы {url}: {e}")
            return None
    
    def extract_title(self, soup):
        """Извлечь название ФГОС"""
        # Ищем в заголовке h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)
        
        # Ищем в title страницы
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)
        
        return "Неизвестный ФГОС"
    
    def extract_code(self, title, url):
        """Извлечь код специальности"""
        # Попробуем найти код в заголовке (например, "37.05.02")
        code_pattern = r'\b\d{2}\.\d{2}\.\d{2}\b'
        match = re.search(code_pattern, title)
        if match:
            return match.group()
        
        # Попробуем найти в URL
        match = re.search(r'fgos-(\d{2}-\d{2}-\d{2})', url)
        if match:
            return match.group(1).replace('-', '.')
        
        return None
    
    def extract_level(self, title):
        """Извлечь уровень образования"""
        title_lower = title.lower()
        
        if 'специалитет' in title_lower:
            return 'Специалитет'
        elif 'бакалавриат' in title_lower:
            return 'Бакалавриат'
        elif 'магистратура' in title_lower:
            return 'Магистратура'
        elif 'аспирантура' in title_lower:
            return 'Аспирантура'
        elif 'среднего профессионального' in title_lower:
            return 'Среднее профессиональное образование'
        elif 'основного общего' in title_lower:
            return 'Основное общее образование'
        elif 'начального общего' in title_lower:
            return 'Начальное общее образование'
        elif 'дошкольного' in title_lower:
            return 'Дошкольное образование'
        
        return None
    
    def extract_field_of_study(self, title):
        """Извлечь область изучения"""
        # Попробуем найти название специальности после кода
        pattern = r'\d{2}\.\d{2}\.\d{2}\s+(.+?)(?:\s*\(|$)'
        match = re.search(pattern, title)
        if match:
            field = match.group(1).strip()
            return field
        
        return None
    
    def find_download_link(self, soup):
        """Найти ссылку на скачивание PDF"""
        # Ищем ссылку с текстом "Скачать"
        download_links = soup.find_all('a', string=re.compile(r'Скачать', re.IGNORECASE))
        
        for link in download_links:
            href = link.get('href')
            if href and 'standart_pdf.php' in href:
                return href
        
        # Ищем по классу кнопки
        download_buttons = soup.find_all('a', class_=re.compile(r'btn.*download|download.*btn', re.IGNORECASE))
        for button in download_buttons:
            href = button.get('href')
            if href and 'standart_pdf.php' in href:
                return href
        
        # Ищем любые ссылки на PDF или standart_pdf.php
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href')
            if href and ('standart_pdf.php' in href or href.endswith('.pdf')):
                return href
        
        return None
    
    def extract_order_number(self, soup):
        """Извлечь номер приказа"""
        text = soup.get_text()
        
        # Ищем номер приказа
        patterns = [
            r'Приказ[^\d]*№\s*(\d+)',
            r'приказ[^\d]*№\s*(\d+)',
            r'№\s*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_ministry(self, soup):
        """Извлечь название министерства"""
        text = soup.get_text()
        
        if 'Министерство образования и науки' in text:
            return 'Министерство образования и науки Российской Федерации'
        elif 'Министерство просвещения' in text:
            return 'Министерство просвещения Российской Федерации'
        
        return None
    
    def extract_registration_number(self, soup):
        """Извлечь регистрационный номер"""
        text = soup.get_text()
        
        # Ищем регистрационный номер
        pattern = r'регистрационный\s*№\s*(\d+)'
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
        
        return None
    
    def extract_published_date(self, soup):
        """Извлечь дату публикации"""
        text = soup.get_text()
        
        # Ищем дату в различных форматах
        date_patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{1,2}\s+\w+\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    if '.' in match:
                        date = datetime.strptime(match, '%d.%m.%Y').date()
                    else:
                        # Попробуем различные форматы с месяцами
                        months = {
                            'января': '01', 'февраля': '02', 'марта': '03',
                            'апреля': '04', 'мая': '05', 'июня': '06',
                            'июля': '07', 'августа': '08', 'сентября': '09',
                            'октября': '10', 'ноября': '11', 'декабря': '12'
                        }
                        
                        for month_name, month_num in months.items():
                            if month_name in match.lower():
                                date_str = re.sub(month_name, month_num, match.lower(), flags=re.IGNORECASE)
                                date_str = re.sub(r'\s+', '.', date_str.strip())
                                date = datetime.strptime(date_str, '%d.%m.%Y').date()
                                break
                        else:
                            continue
                    
                    return date
                except ValueError:
                    continue
        
        return None
    
    def download_pdf(self, url, file_path):
        """Скачать PDF файл"""
        try:
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            # Проверяем, что это PDF файл
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not url.endswith('.pdf'):
                # Проверяем по содержимому
                if not response.content.startswith(b'%PDF'):
                    print(f"Файл по ссылке {url} не является PDF")
                    return False, "Файл не является PDF"
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            file_size = len(response.content)
            print(f"Скачан файл {file_path} ({file_size} байт)")
            return True, file_size
            
        except requests.RequestException as e:
            error_msg = f"Ошибка при скачивании файла {url}: {e}"
            print(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Неожиданная ошибка при скачивании файла {url}: {e}"
            print(error_msg)
            return False, error_msg
    
    def save_or_update_document(self, document_data):
        """Сохранить или обновить документ в базе данных"""
        try:
            # Проверяем, существует ли уже такой документ
            existing_doc = None
            
            if document_data.get('code'):
                existing_doc = FgosDocument.objects.filter(
                    code=document_data['code'],
                    level=document_data['level']
                ).first()
            
            if existing_doc:
                # Обновляем существующий документ
                for key, value in document_data.items():
                    if value is not None:
                        setattr(existing_doc, key, value)
                existing_doc.updated_at = timezone.now()
                existing_doc.save()
                
                if self.parsing_session:
                    self.parsing_session.documents_updated += 1
                    self.parsing_session.save()
                
                return existing_doc, False  # False = не новый
            else:
                # Создаем новый документ
                document_data['filename'] = f"{document_data.get('code', 'unknown')}.pdf"
                doc = FgosDocument.objects.create(**document_data)
                
                if self.parsing_session:
                    self.parsing_session.new_documents_added += 1
                    self.parsing_session.save()
                
                return doc, True  # True = новый
                
        except Exception as e:
            print(f"Ошибка при сохранении документа: {e}")
            return None, False
    
    def run_full_parsing(self):
        """Запустить полный парсинг сайта"""
        print("Начинаем парсинг сайта fgos.ru")
        
        # Начинаем сессию парсинга
        session = self.start_parsing_session()
        print(f"Создана сессия парсинга: {session.id}")
        
        try:
            # Шаг 1: Найти все ссылки на ФГОС
            print("Поиск ссылок на страницы ФГОС...")
            fgos_links = self.find_fgos_links()
            
            if not fgos_links:
                print("Не найдено ссылок на ФГОС")
                session.mark_failed("Не найдено ссылок на ФГОС")
                return session
            
            # Шаг 2: Парсить каждую страницу ФГОС
            print(f"Начинаем парсинг {len(fgos_links)} страниц...")
            
            for i, url in enumerate(fgos_links, 1):
                print(f"[{i}/{len(fgos_links)}] Парсинг: {url}")
                
                try:
                    # Парсим страницу
                    document_data = self.parse_fgos_page(url)
                    if not document_data:
                        print(f"Не удалось извлечь данные со страницы {url}")
                        continue
                    
                    # Сохраняем в БД
                    doc, is_new = self.save_or_update_document(document_data)
                    if not doc:
                        print(f"Не удалось сохранить документ для страницы {url}")
                        continue
                    
                    session.total_documents_found += 1
                    
                    # Скачиваем PDF файл
                    file_path = os.path.join(self.media_path, f"{doc.uuid}.pdf")
                    success, result = self.download_pdf(document_data['download_url'], file_path)
                    
                    if success:
                        doc.is_downloaded = True
                        doc.file_size = result
                        doc.download_error = None
                        session.files_downloaded += 1
                        print(f"✓ Файл успешно скачан: {doc.title}")
                    else:
                        doc.is_downloaded = False
                        doc.download_error = str(result)
                        session.download_errors += 1
                        print(f"✗ Ошибка скачивания файла: {doc.title}")
                    
                    doc.save()
                    session.save()
                    
                    # Небольшая задержка между запросами
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"Ошибка при обработке страницы {url}: {e}")
                    session.download_errors += 1
                    session.save()
                    continue
            
            # Завершаем сессию
            session.mark_completed()
            print(f"Парсинг завершен успешно!")
            print(f"Всего документов найдено: {session.total_documents_found}")
            print(f"Новых документов добавлено: {session.new_documents_added}")
            print(f"Документов обновлено: {session.documents_updated}")
            print(f"Файлов скачано: {session.files_downloaded}")
            print(f"Ошибок скачивания: {session.download_errors}")
            
        except Exception as e:
            error_msg = f"Критическая ошибка при парсинге: {e}"
            print(error_msg)
            session.mark_failed(error_msg)
        
        return session 