"""Główny program weryfikacji nauczyciela Verify1D (K12)"""
import re
import random
import logging
import httpx
from typing import Dict, Optional, Tuple

# Import jako pakiet lub skrypt
try:
    from . import config  # type: ignore
    from .name_generator import NameGenerator, generate_email, generate_birth_date  # type: ignore
    from .img_generator import generate_teacher_pdf, generate_teacher_png  # type: ignore
except ImportError:
    import config  # type: ignore
    from name_generator import NameGenerator, generate_email, generate_birth_date  # type: ignore
    from img_generator import generate_teacher_pdf, generate_teacher_png  # type: ignore

# Stałe z config
PROGRAM_ID = config.PROGRAM_ID
SHEERID_BASE_URL = config.SHEERID_BASE_URL
MY_SHEERID_URL = config.MY_SHEERID_URL
SCHOOLS = config.SCHOOLS
DEFAULT_SCHOOL_ID = config.DEFAULT_SCHOOL_ID


logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SheerIDVerifier:
    """Weryfikator tożsamości nauczyciela Verify1D"""

    def __init__(self, verification_id: str):
        """verification_id: identyfikator weryfikacji Verify1D"""
        self.verification_id = verification_id
        self.device_fingerprint = self._generate_device_fingerprint()
        self.http_client = httpx.Client(timeout=30.0)

    def __del__(self):
        """Zamyka klienta HTTP."""
        if hasattr(self, 'http_client'):
            self.http_client.close()

    @staticmethod
    def _generate_device_fingerprint() -> str:
        """Odcisk urządzenia."""
        chars = '0123456789abcdef'
        return ''.join(random.choice(chars) for _ in range(32))

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalizacja URL."""
        return url

    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        """Wyciąga verificationId z URL."""
        match = re.search(r'verificationId=([a-f0-9]+)', url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _sheerid_request(self, method: str, url: str,
                         body: Optional[Dict] = None) -> Tuple[Dict, int]:
        """Żądanie do API Verify1D."""
        headers = {
            'Content-Type': 'application/json',
        }

        try:
            response = self.http_client.request(
                method=method,
                url=url,
                json=body,
                headers=headers
            )

            try:
                data = response.json()
            except Exception:
                data = response.text

            return data, response.status_code
        except Exception as e:
            logger.error("Żądanie Verify1D nie powiodło się: %s", e)
            raise

    def _upload_to_s3(self, upload_url: str, content: bytes, mime_type: str) -> bool:
        """Wgrywanie pliku do S3."""
        try:
            headers = {
                'Content-Type': mime_type,
            }
            response = self.http_client.put(
                upload_url,
                content=content,
                headers=headers,
                timeout=60.0
            )
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error("Wgrywanie S3 nie powiodło się: %s", e)
            return False

    def verify(self, first_name: str = None, last_name: str = None,
               email: str = None, birth_date: str = None,
               school_id: str = None,
               hcaptcha_token: str = None, turnstile_token: str = None) -> Dict:
        """Pełny przebieg weryfikacji bez długiego pollingu statusu."""
        try:
            current_step = 'initial'

            if not first_name or not last_name:
                name = NameGenerator.generate()
                first_name = name['first_name']
                last_name = name['last_name']

            school_id = school_id or DEFAULT_SCHOOL_ID
            school = SCHOOLS[school_id]

            if not email:
                email = generate_email()

            if not birth_date:
                birth_date = generate_birth_date()

            logger.info("Nauczyciel: %s %s", first_name, last_name)
            logger.info("E-mail: %s", email)
            logger.info("Szkoła: %s", school['name'])
            logger.info("Data urodzenia: %s", birth_date)
            logger.info("ID weryfikacji: %s", self.verification_id)

            logger.info("Krok 1/4: generowanie PDF i PNG potwierdzenia...")
            pdf_data = generate_teacher_pdf(first_name, last_name)
            png_data = generate_teacher_png(first_name, last_name)
            pdf_size = len(pdf_data)
            png_size = len(png_data)
            logger.info("PDF: %.2f KB, PNG: %.2f KB", pdf_size / 1024, png_size / 1024)

            logger.info("Krok 2/4: wysyłka danych nauczyciela...")
            step2_body = {
                'firstName': first_name,
                'lastName': last_name,
                'birthDate': birth_date,
                'email': email,
                'phoneNumber': '',
                'organization': {
                    'id': school['id'],
                    'idExtended': school['idExtended'],
                    'name': school['name']
                },
                'deviceFingerprintHash': self.device_fingerprint,
                'locale': 'en-US',
                'metadata': {
                    'marketConsentValue': False,
                    'refererUrl': f"{SHEERID_BASE_URL}/verify/{PROGRAM_ID}/?verificationId={self.verification_id}",
                    'verificationId': self.verification_id,
                    'submissionOptIn': 'By submitting the personal information above, I acknowledge that my personal information is being collected under the privacy policy of the business from which I am seeking a discount'
                }
            }

            step2_data, step2_status = self._sheerid_request(
                'POST',
                f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectTeacherPersonalInfo",
                step2_body
            )

            if step2_status != 200:
                raise Exception(f"Krok 2 nieudany (HTTP {step2_status}): {step2_data}")

            if step2_data.get('currentStep') == 'error':
                error_msg = ', '.join(step2_data.get('errorIds', ['Unknown error']))
                raise Exception(f"Błąd kroku 2: {error_msg}")

            logger.info("Krok 2 zakończony: %s", step2_data.get('currentStep'))
            current_step = step2_data.get('currentStep', current_step)

            if current_step in ['sso', 'collectTeacherPersonalInfo']:
                logger.info("Krok 3/4: pomijanie SSO...")
                step3_data, _ = self._sheerid_request(
                    'DELETE',
                    f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso"
                )
                logger.info("Krok 3 zakończony: %s", step3_data.get('currentStep'))
                current_step = step3_data.get('currentStep', current_step)

            logger.info("Krok 4/4: dokumenty i wgrywanie...")
            step4_body = {
                'files': [
                    {
                        'fileName': 'teacher_document.pdf',
                        'mimeType': 'application/pdf',
                        'fileSize': pdf_size
                    },
                    {
                        'fileName': 'teacher_document.png',
                        'mimeType': 'image/png',
                        'fileSize': png_size
                    }
                ]
            }

            step4_data, step4_status = self._sheerid_request(
                'POST',
                f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
                step4_body
            )

            documents = step4_data.get('documents') or []
            if len(documents) < 2:
                raise Exception("Nie udało się uzyskać URL do wgrywania")

            pdf_upload_url = documents[0]['uploadUrl']
            png_upload_url = documents[1]['uploadUrl']
            logger.info("URL wgrywania uzyskany")

            if not self._upload_to_s3(pdf_upload_url, pdf_data, 'application/pdf'):
                raise Exception("Wgrywanie PDF nie powiodło się")
            if not self._upload_to_s3(png_upload_url, png_data, 'image/png'):
                raise Exception("Wgrywanie PNG nie powiodło się")
            logger.info("PDF i PNG wgrane")

            step6_data, _ = self._sheerid_request(
                'POST',
                f"{SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/completeDocUpload"
            )
            logger.info("Dokumenty złożone: %s", step6_data.get('currentStep'))
            final_status = step6_data

            return {
                'success': True,
                'pending': True,
                'message': 'Dokument przesłany, oczekuje na weryfikację',
                'verification_id': self.verification_id,
                'redirect_url': final_status.get('redirectUrl'),
                'status': final_status
            }

        except Exception as e:
            logger.error("Weryfikacja nie powiodła się: %s", e)
            return {
                'success': False,
                'message': str(e),
                'verification_id': self.verification_id
            }
