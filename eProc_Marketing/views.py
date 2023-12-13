import io
import csv
import os
import re
import datetime
import time
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from io import TextIOWrapper
from io import StringIO
from django.views.decorators.csrf import csrf_exempt
from flask.app import Flask

app = Flask(__name__)

try:
    if 'DISPLAY' in os.environ:
        import pywhatkit as kit

        pywhatkit_available = True
    else:
        print("No DISPLAY environment variable found. Skipping pywhatkit import.")
        pywhatkit_available = False
except ImportError:
    print("pywhatkit is not available. WhatsApp functionality will be disabled.")
    pywhatkit_available = False


def index(request):
    context = {
        'inc_nav': True,
        'inc_footer': True,
        'is_slide_menu': True,
        'is_configuration_active': True
    }
    return render(request, 'eProc_Marketing/marketing.html', context)


def send_whatsapp_message(phone_number, message, image_path, send_time):
    try:
        if not message and not image_path:
            print("Both message and image are missing. Nothing to send.")
            return

        now = datetime.datetime.now()
        delay = (send_time - now).total_seconds()

        if delay > 0:
            print(f"Waiting for {delay} seconds until the scheduled send time.")
            time.sleep(delay)

        if message or image_path:
            if pywhatkit_available:
                kit.sendwhats_image(phone_number, image_path, caption=message)

                # Wait for a few seconds before moving on
                time.sleep(5)

                print(f"Message sent successfully to {phone_number}")

    except Exception as e:
        print(f'Error sending message to {phone_number}: {str(e)}')
        import traceback
        traceback.print_exc()


@csrf_exempt
def send_message(request):
    global image_path
    try:
        message = request.POST['message']
        start_hours = int(request.POST['hours'].strip('"'))
        start_minutes = int(request.POST['minutes'])
        csv_file = request.FILES['csv']
        image_file = request.FILES.get('image')

        if image_file and pywhatkit_available:
            image_path = os.path.join(settings.MEDIA_ROOT, 'image.jpg')
            with open(image_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

        csv_content = csv_file.read().decode('utf-8', errors='replace')
        text_csv_file = StringIO(csv_content)

        phone_numbers = []
        with csv_file.open(mode='rb') as file:
            csv_content = re.sub(rb'[^\x00-\x7F]+', b'', file.read())
            text_csv_file = TextIOWrapper(io.BytesIO(csv_content), encoding='utf-8')

            reader = csv.DictReader(text_csv_file)
            for row in reader:
                if 'phone_number' in row:
                    phone_number = row['phone_number']
                    if not phone_number.startswith('+'):
                        phone_number = '+91' + phone_number

                    phone_numbers.append(phone_number)

        interval = datetime.timedelta(minutes=1)
        now = datetime.datetime.now()
        send_time = now.replace(hour=start_hours, minute=start_minutes, second=0, microsecond=0) + datetime.timedelta(
            seconds=5)

        for phone_number in phone_numbers:
            try:
                send_whatsapp_message(phone_number, message, image_path, send_time)
                send_time += interval

                if send_time.minute >= 60:
                    send_time = send_time.replace(hour=send_time.hour + 1, minute=send_time.minute % 60)

            except Exception as e:
                print(f'Error sending message to {phone_number}: {str(e)}')

        return JsonResponse({'result': 'Messages sent successfully'})
    except Exception as e:
        print(f'Error: {str(e)}')
        return JsonResponse({'result': f'Error: {str(e)}'})


if __name__ == '__main__':
    app.run(debug=True)
