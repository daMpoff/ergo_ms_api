import os
import io
import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # headless backend for servers
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.auth import get_user_model

from src.modules.impuls_analysis.tasks import create_analysis_by_protocol

logger = logging.getLogger('impuls_analysis')


class Command(BaseCommand):
	help = 'Создает анализ по номеру протокола: строит 2 графика и сохраняет таблицу максимумов в БД.'

	def add_arguments(self, parser):
		parser.add_argument('--protocol', required=True, help='Номер протокола (как в Excel/БД)')
		parser.add_argument('--user_id', required=True, type=int, help='ID пользователя для привязки анализа')
		parser.add_argument('--title', required=False, help='Название анализа (по умолчанию сгенерируется)')
		parser.add_argument('--description', required=False, help='Описание анализа')

	def handle(self, *args, **options):
		protocol_number: str = str(options['protocol']).strip()
		user_id: int = int(options['user_id'])
		title: Optional[str] = options.get('title')
		description: Optional[str] = options.get('description')

		# Проверяем, существует ли уже анализ
		from django.contrib.auth import get_user_model
		from src.modules.impuls_analysis.models import ImpulsAnalysis
		
		User = get_user_model()
		user = User.objects.filter(id=user_id).first()
		if user is None:
			raise CommandError(f'Пользователь не найден (id={user_id})')
		
		existing_analysis = ImpulsAnalysis.objects.filter(
			user=user, 
			protocol_number=protocol_number
		).first()
		
		if existing_analysis:
			self.stdout.write(self.style.WARNING(
				f'Найден существующий анализ для протокола {protocol_number} (id={existing_analysis.id}). '
				f'Статус: {existing_analysis.get_status_display()}. '
				f'Создан: {existing_analysis.created_at.strftime("%d.%m.%Y %H:%M")}. '
				f'Старый анализ будет удален и создан новый.'
			))

		# Запуск Celery задачи
		async_result = create_analysis_by_protocol.delay(protocol_number, user_id, title or None, description or None)
		self.stdout.write(self.style.SUCCESS(
			f'Задача анализа запущена (task_id={async_result.id}). Протокол: {protocol_number}, user_id={user_id}'
		))
