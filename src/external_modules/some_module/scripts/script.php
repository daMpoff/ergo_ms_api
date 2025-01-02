<?php
// function factorial($n) {
//     if ($n < 0) {
//         return "Факториал не определен для отрицательных чисел";
//     }
//     if ($n == 0 || $n == 1) {
//         return 1;
//     }
//     return $n * factorial($n - 1);
// }

// $number = 5;
// $result = factorial($number);

// echo "Факториал $number равен $result";

// Параметры подключения к базе данных
$host = "localhost"; // Имя хоста
$port = "5432"; // Порт (по умолчанию 5432)
$dbname = "oms"; // Имя базы данных
$user = "postgres"; // Имя пользователя
$password = "admin"; // Пароль

// Строка подключения
$conn_string = "host=$host port=$port dbname=$dbname user=$user password=$password";

// Подключение к базе данных
$conn = pg_connect($conn_string);

// Проверка подключения
if (!$conn) {
    die("Подключение не удалось: " . pg_last_error());
}
echo "Подключение успешно";

// Закрытие подключения
pg_close($conn);

?>