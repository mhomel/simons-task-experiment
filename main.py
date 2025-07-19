#!/usr/bin/env python
# -*- coding: utf-8 -*-
# === Importowanie bibliotek i modułów ===
# Używamy m.in. do obsługi plików, losowości, PsychoPy, okien dialogowych, logowania itp.
import csv
import yaml
import random
import atexit
import codecs
import os

from typing import List, Dict
from os.path import join
from psychopy import visual, event, logging, gui, core




@atexit.register
def save_beh_results() -> None:
# Funkcja automatycznie zapisywana na koniec eksperymentu.
# Tworzy plik .csv z wynikami zachowań uczestnika (reaction time, poprawność)
    file_name = PART_ID + '_' + str(random.choice(range(100, 1000))) + '_beh.csv'
    with open(join('results', file_name), 'w', encoding='utf-8') as beh_file:
        beh_writer = csv.writer(beh_file)
        beh_writer.writerows(RESULTS)
    logging.flush()


def read_text_from_file(file_name: str, insert: str = '') -> str:
# Wczytuje treść instrukcji z pliku tekstowego (.txt).
# Jeśli znajdzie linię z '<--insert-->', to wstawia podany tekst (np. imię).
    if not isinstance(file_name, str):
        logging.error('Problem with file reading, filename must be a string')
        raise TypeError('file_name must be a string')
    msg = list()
    with codecs.open(file_name, encoding='utf-8', mode='r') as data_file:
        for line in data_file:
            if not line.startswith('#'):  # if not commented line
                if line.startswith('<--insert-->'):
                    if insert:
                        msg.append(insert)
                else:
                    msg.append(line)
    return ''.join(msg)


def check_exit() -> None:
# Sprawdza, czy użytkownik nacisnął klawisz ESC.
# Jeśli tak – zapisuje informację w logach i kończy eksperyment natychmiast.
# Wywoływana w wielu miejscach w kodzie, żeby ESC działał zawsze. 
    if 'escape' in event.getKeys():
        logging.critical("Eksperyment przerwany przez użytkownika (ESC).")
        win.close()
        core.quit()


def show_info(win: visual.Window, file_name: str, insert: str = '') -> None:
# Wyświetla ekran tekstowy z pliku (np. instrukcje, przerwy, zakończenie).
# Czeka na naciśnięcie przycisku (np. spacji lub Enter).
# Obsługuje też specjalny znacznik <--insert--> i klawisz F7 jako przerwanie eksperymentu.
    msg = read_text_from_file(file_name, insert=insert)
    msg = visual.TextStim(win, color='black', text=msg, height=20, wrapWidth=1000)
    msg.draw()
    win.flip()
    check_exit()
    key = event.waitKeys(keyList=['f7', 'return', 'space', 'left', 'right'],
                         maxWait=conf['MAX_WAIT'] / conf['FRAME_RATE'])
    if key == ['f7']:
        abort_with_error('Experiment finished by user on info screen! F7 pressed.')
    win.flip()

def abort_with_error(err: str) -> None:
# Funkcja pomocnicza do awaryjnego zatrzymania eksperymentu z komunikatem błędu.
# Zapisuje komunikat do logów, zgłasza wyjątek i przerywa działanie programu.
    logging.critical(err)
    raise Exception(err)

# Przeprowadza jedną próbę eksperymentalną:
def run_trial(win, conf, clock, stim):
    # === Prepare trial-related stimulus ===

    # 1. Pokazuje punkt fiksacji.
    for _ in range(conf['FIX_CROSS_TIME']):
        fix_cross.draw()
        win.flip()

    # === Start trial ===

    # 2. Prezentuje bodziec i zbiera reakcję.
    event.clearEvents()
    win.callOnFlip(clock.reset)

    for _ in range(conf['STIM_TIME']):  # prezentuj bodziec
        reaction = event.getKeys(keyList=list(conf['REACTION_KEYS']), timeStamped=clock)
        if 'escape' in event.getKeys():
            logging.critical("Eksperyment przerwany przez użytkownika (ESC).")
            win.close()
            core.quit()
        if reaction:  # przerwij jeśli uczestnik zareagował
            break
        stim.draw()
        win.flip()

    if not reaction:    # Jeśli brak reakcji w czasie STIM_TIME – daj czas na reakcję po zniknięciu bodźca
        win.flip()
        reaction = event.waitKeys(keyList=list(conf['REACTION_KEYS']),
                                  maxWait=conf['REACTION_TIME'] / conf['FRAME_RATE'],
                                  timeStamped=clock)

    # === Trial ended, prepare data for send  ===

    # 3. Zbiera dane o czasie reakcji i naciśniętym klawiszu
    if reaction:
        key_pressed, rt = reaction[0]
    else:  # timeout
        key_pressed = 'no_key'
        rt = -1.0

    # 4. Obsługuje ESC (gdyby naciśnięto podczas czekania)
    check_exit()
    return key_pressed, rt  # Zwraca wszystkie dane zebrane podczas próby


# GLOBAL VARIABLES : Inicjalizacja zmiennych globalnych i konfiguracji

# Zbieranie wyników

RESULTS = list()  # list in which data will be collected
RESULTS.append(['PART_ID', 'Trial_no', 'Reaction time', 'Correctness'])  # Results header
PART_ID = ''
SCREEN_RES = []

# === Dialog popup ===
info: Dict = {'ID': '', 'Sex': ['M', "F"], 'Age': '20'}
dict_dlg = gui.DlgFromDict(dictionary=info, title='Experiment title, fill by your name!')
if not dict_dlg.OK:
    abort_with_error('Info dialog terminated.')

clock = core.Clock()
# load config, all params should be there
conf: Dict = yaml.load(open('config.yaml', encoding='utf-8'), Loader=yaml.SafeLoader)
frame_rate: int = conf['FRAME_RATE']
SCREEN_RES: List[int] = conf['SCREEN_RES']

# === Scene init ===

# Tworzymy okno PsychoPy
win = visual.Window(SCREEN_RES, fullscr=True, monitor='testMonitor',
                    units='pix', color=conf['BACKGROUND_COLOR'])

# Ukrywamy kursor myszy
event.Mouse(visible=False, newPos=None, win=win)  

# Tworzymy folder na wyniki, jeśli nie istnieje
if not os.path.exists('results'):
    os.makedirs('results')

# Tworzymy unikalny identyfikator uczestnika na podstawie danych z dialogu
PART_ID = info['ID'] + info['Sex'] + info['Age']

# Uruchamiamy plik logów (zapisuje zdarzenia eksperymentu)
logging.LogFile(join('results', f'{PART_ID}.log'), level=logging.INFO)  # errors logging
logging.info('FRAME RATE: {}'.format(frame_rate))
logging.info('SCREEN RES: {}'.format(SCREEN_RES))

# === Prepare stimulus here ===
# Tworzymy:

# punkt fiksacji (fixation cross),
fix_cross = visual.TextStim(
    win,
    text='+',
    height=conf['FIX_CROSS_SIZE'],
    color=conf['FIX_CROSS_COLOR']
)

# słowa LEFT/RIGHT w wersjach zgodnych i niezgodnych (po lewej lub prawej stronie ekranu).
# Pozycje są przesuwane w poziomie o wartość STIM_SHIFT (z config.yaml).
stim_ll = visual.TextStim(win, text='LEFT', height=conf['STIM_SIZE'], color=conf['STIM_COLOR'],
                          pos=[-conf['STIM_SHIFT'], 0])  # bodziec LEFT zgodny
stim_lr = visual.TextStim(win, text='LEFT', height=conf['STIM_SIZE'], color=conf['STIM_COLOR'],
                          pos=[conf['STIM_SHIFT'], 0])  # bodziec LEFT niezgodny
stim_rr = visual.TextStim(win, text='RIGHT', height=conf['STIM_SIZE'], color=conf['STIM_COLOR'],
                          pos=[conf['STIM_SHIFT'], 0])  # bodziec RIGHT zgodny
stim_rl = visual.TextStim(win, text='RIGHT', height=conf['STIM_SIZE'], color=conf['STIM_COLOR'],
                          pos=[-conf['STIM_SHIFT'], 0])  # bodziec RIGHT niezgodny

# Logujemy najważniejsze parametry bodźców (dla kontroli poprawności).
# Te dane będą zapisane w pliku .log, który jest zapisywany w results/ razem z innymi zdarzeniami eksperymentu.
logging.info("Fixation cross configured with size {} and color {}".format(conf['FIX_CROSS_SIZE'],
                                                                        conf['FIX_CROSS_COLOR']))
logging.info("Stimuli configured with size {}, color {}, and shift {}".format(conf['STIM_SIZE'],
                                                                              conf['STIM_COLOR'],
                                                                              conf['STIM_SHIFT']))

# Grupujemy bodźce:

stim_con = [stim_ll, stim_rr] # stim_con – bodźce zgodne (LEFT po lewej, RIGHT po prawej)
stim_l = [stim_ll, stim_lr] # stim_l – bodźce z tekstem LEFT (niezależnie od strony)
stim_r = [stim_rr, stim_rl] # stim_r – bodźce z tekstem RIGHT (niezależnie od strony)

# === Training ===
# Tworzymy listę bodźców treningowych w równych proporcjach (po 1/4 każdego typu).
# Każdy element to słownik z obiektem bodźca i poprawnym klawiszem.
# Następnie losujemy ich kolejność – z warunkiem: nie może być więcej niż 4 bodźce zgodne z rzędu.

stims = (
        [{'stim': stim_ll, 'correct_key': 'z'}] * int(conf['NO_TRAINING_TRIALS'] / 4) +
        [{'stim': stim_lr, 'correct_key': 'z'}] * int(conf['NO_TRAINING_TRIALS'] / 4) +
        [{'stim': stim_rr, 'correct_key': 'm'}] * int(conf['NO_TRAINING_TRIALS'] / 4) +
        [{'stim': stim_rl, 'correct_key': 'm'}] * int(conf['NO_TRAINING_TRIALS'] / 4)
)

# Flaga kontrolna – dopóki warunek powtórzeń nie jest spełniony, mieszamy dalej
stims_ready = False
while not stims_ready:
    # Losujemy kolejność bodźców
    random.shuffle(stims)
    max_rep = 1
    stims_ready = True

    # Sprawdzamy, czy nie ma zbyt wielu bodźców zgodnych z rzędu
    for i in range(1, conf['NO_TRAINING_TRIALS']):
        # Jeśli aktualny bodziec i poprzedni to bodźce zgodne
        if stims[i] in stim_con and stims[i - 1] in stim_con:
            # Zwiększamy licznik powtórzeń
            max_rep += 1
        else:
            # Jeśli pojawił się inny typ bodźca – resetujemy licznik powtórzeń
            max_rep = 1

        # Jeśli liczba powtórzeń zgodnych przekracza dozwolony limit – losujemy jeszcze raz
        if max_rep > conf['TRIALS_REPETITION']:
            # Oznaczamy, że sekwencja nie spełnia warunku → trzeba wylosować od nowa
            stims_ready = False
            # Przerywamy sprawdzanie – nie ma sensu dalej analizować tej sekwencji
            break

# Wyświetlamy instrukcję przed rozpoczęciem treningu (plik tekstowy).
show_info(win, join('.', 'messages', 'before_training.txt'))


# === Przebieg prób treningowych ===
# - zerujemy liczniki,

# Dla każdej próby (każdy pojedyczy bodziec):
# – uruchamiamy funkcję run_trial(),
# – sprawdzamy, czy reakcja była poprawna i zbieramy czas reakcji z każdej próby
# - feedback o średnich czasach reakcji
# – zapisujemy dane (klawisz, RT, poprawność)

correct_counter = 0 # Zerujemy liczbe poprawnych odpowiedzi, aby po każdej próbie liczyło od nowa
avg_rt_con = 0  # Zerujemy średni czas reakcji dla bodźców zgodnych, aby po każdej próbie liczyło od nowa
avg_rt_inc = 0 # Zerujemy średni czas reakcji dla bodźców niezgodnych, aby po każdej próbie liczyło od nowa

for trial_no in range(conf['NO_TRAINING_TRIALS']):
    key_pressed, rt = run_trial(win, conf, clock, stims[trial_no]['stim'])
    if (key_pressed == 'z' and (stims[trial_no]['stim'] in stim_l)) or (
            key_pressed == 'm' and (stims[trial_no]['stim'] in stim_r)):  # prawidłowo naciśnięty przycisk
        corr = True
    else:  # brak reakcji / zły przycisk
        corr = False
    RESULTS.append([PART_ID, trial_no, rt, corr])

    # Sumujemy czasy reakcji i liczymy średni czas reakcji oddzielnie dla bodźców zgodnych i niezgodnych
    if key_pressed and (stims[trial_no]['stim'] in stim_con):
        avg_rt_con += rt # bodźce zgodne

    elif key_pressed:
        avg_rt_inc += rt # bodźce niezgodne

    # Wyświetlamy informację zwrotną – poprawna lub błędna odpowiedź po każdej próbie
    if corr:
        feedb = visual.TextStim(win, text=conf['FEEDBACK_CORRECT_TEXT'],
                                height=conf['STIM_SIZE'],
                                color=conf['FEEDBACK_COLOR_CORRECT'])
        correct_counter += 1 # licznik poprawnych odpowiedzi
    else:
        feedb = visual.TextStim(win, text=conf['FEEDBACK_INCORRECT_TEXT'],
                                height=conf['STIM_SIZE'],
                                color=conf['FEEDBACK_COLOR_INCORRECT'])

    for frameN in range(conf['FEEDBACK_TIME']):
        check_exit()
        feedb.draw()
        win.flip()

    # Wstawiamy losową przerwę (jitter) między próbami, by uniknąć przewidywalności
    jitter_frames = random.randint(*conf['JITTER_TIME_RANGE'])
    for _ in range(jitter_frames):
        check_exit()
        win.flip()

# === Podsumowanie treningu ===
# Obliczamy średni czas reakcji dla bodźców zgodnych i niezgodnych.
# Wyświetlamy wynik uczestnikowi i czekamy na naciśnięcie spacji.
avg_rt_con /= (conf['NO_TRAINING_TRIALS'] / 2)
avg_rt_inc /= (conf['NO_TRAINING_TRIALS'] / 2)

summary_text = (f"Średni czas reakcji dla bodźców zgodnych: {avg_rt_con * 1000:.0f} ms\n "
                f"Średni czas reakcji dla bodźców niezgodnych: {avg_rt_inc * 1000:.0f} ms\n"
                f"Liczba poprawnych odpowiedzi: {correct_counter} z {conf['NO_TRAINING_TRIALS']}\n"
                f"Naciśnij spację, żeby przejść dalej.")


# Tworzymy obiekt tekstowy do wyświetlenia podsumowania na ekranie
summary_msg = visual.TextStim(win, text=summary_text, height=40, color='white', wrapWidth=1000)
summary_msg.draw()
win.flip()
event.waitKeys(keyList=['space'])  # czekamy na spację, by kontynuować
win.flip()

# === Experiment ===
# Tworzymy listę bodźców eksperymentalnych w równych proporcjach (po 1/4 każdego typu).
# Każdy element to słownik z obiektem bodźca i poprawnym klawiszem.
# Następnie losujemy ich kolejność – z warunkiem: nie może być więcej niż 4 bodźce zgodne z rzędu. 

stims = (
        [{'stim': stim_ll, 'correct_key': 'z'}] * int(conf['NO_TRAINING_TRIALS'] / 4) +
        [{'stim': stim_lr, 'correct_key': 'z'}] * int(conf['NO_TRAINING_TRIALS'] / 4) +
        [{'stim': stim_rr, 'correct_key': 'm'}] * int(conf['NO_TRAINING_TRIALS'] / 4) +
        [{'stim': stim_rl, 'correct_key': 'm'}] * int(conf['NO_TRAINING_TRIALS'] / 4)
)

# Flaga kontrolna – dopóki warunek powtórzeń nie jest spełniony, mieszamy dalej
stims_ready = False
while not stims_ready:
    check_exit()
    # Losujemy kolejność bodźców
    random.shuffle(stims)
    max_rep = 1
    stims_ready = True
    # Sprawdzamy, czy nie ma zbyt wielu bodźców zgodnych z rzędu
    for i in range(1, conf['TRIALS_IN_BLOCK']):
        if stims[i] in stim_con and stims[i - 1] in stim_con:
            # Zwiększamy licznik powtórzeń
            max_rep += 1
        else:
            # Jeśli pojawił się inny typ bodźca – resetujemy licznik powtórzeń
            max_rep = 1
        # Jeśli liczba powtórzeń zgodnych przekracza dozwolony limit – losujemy jeszcze raz    
        if max_rep > conf['TRIALS_REPETITION']:
            # Oznaczamy, że sekwencja nie spełnia warunku → trzeba wylosować od nowa
            stims_ready = False
            # Przerywamy sprawdzanie – nie ma sensu dalej analizować tej sekwencji
            break


# === Przebieg eksperymentu właściwego (część blokowa) ===
show_info(win, join('.', 'messages', 'before_experiment.txt'))
# Dla każdego bloku:
# – wykonujemy określoną liczbę prób (TRIALS_IN_BLOCK),
# – każda próba działa jak w treningu: run_trial(), sprawdzenie poprawności, zapis do wyników.
# Po każdym bloku pokazujemy ekran przerwy.
trial_no = 0 # licznik prób (zerujemy przed eksperymentem)
block_no = 0 # licznik bloków (zerujemy przed eksperymentem)
for block_no in range(conf['NO_BLOCKS']): # liczba bloków (sesji)
    for _ in range(conf['TRIALS_IN_BLOCK']): # liczba powtórzeń bloków (sesji)
        key_pressed, rt = run_trial(win, conf, clock, stims[trial_no]['stim'])
        # Sprawdzenie poprawności odpowiedzi na podstawie słownika bodźca
        if key_pressed == stims[trial_no]['correct_key']:
            corr = True
        else:  # brak reakcji, zły przycisk
            corr = False
        RESULTS.append([PART_ID, trial_no, rt, corr]) # zapisujemy wyniki

        trial_no += 1 # po każdym bodźcu zwiększamy licznik

        # Losowa przerwa (jitter) między próbami w bloku
        jitter_frames = random.randint(*conf['JITTER_TIME_RANGE'])
        for _ in range(jitter_frames):
            win.flip()
            
    block_no += 1 # licznik bloków zwiększamy
    # Ekran przerwy po każdym bloku
    show_info(win, join('.', 'messages', 'break.txt'))

# === Zakończenie eksperymentu ===

save_beh_results() # Zapisujemy wyniki do pliku .csv
logging.flush() # kończymy logowanie
show_info(win, join('.', 'messages', 'end.txt')) # Wyświetlamy ekran końcowy
win.close() # Zamykamy okno PsychoPy.

# Koniec eksperymentu. Dziękujemy <3
