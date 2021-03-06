# This is a GUI wrapper for the ReadifyFontCLI script, written in PyQt5.
#
# Created by Sherman Perry

from __future__ import absolute_import, division, print_function, unicode_literals
from PyQt5.QtWidgets import QWidget, QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, \
    QLineEdit, QCheckBox, QComboBox, QRadioButton, QSlider, QLabel, QPushButton, QFileDialog, QTextEdit, \
    QProgressBar, QMessageBox
from PyQt5.QtCore import Qt, QProcess, QDir
from PyQt5.QtGui import QFont, QFontDatabase
from FontInfo import FontInfo
import os
import sys
import helper
import shutil

SEL_REGULAR = 1
SEL_ITALIC = 2
SEL_BOLD = 3
SEL_BOLDITALIC = 4
SEL_NONE = 0

class RF_Qt(QMainWindow):
    """
    Class to create the main GUI window. It extends QMainWindow.
    The GUI allows the user to load up to four font files, provide a new font name, adjust some options,
    view a preview of font changes, and finally generate new TrueType font files.
    """
    def __init__(self):
        """
        Create the main window.
        :return:
        """
        super(RF_Qt, self).__init__()

        # Define variables
        self.fnt_styles = ['Regular', 'Italic', 'Bold', 'Bold Italic']
        self.fnt_sty_combo_list = []
        self.fnt_file_name_list = []
        self.font_files = None
        self.font_info = FontInfo()
        # Create a QProcess object, and connect it to appropriate slots
        self.cli_process = QProcess(self)
        self.cli_process.setProcessChannelMode(QProcess.MergedChannels)
        self.cli_process.readyRead.connect(self.read_proc_output)
        self.cli_process.started.connect(self.manage_proc)
        self.cli_process.finished.connect(self.manage_proc)
        self.cli_process.error.connect(self.manage_proc)

        # Style for all groupbox labels
        gb_style = 'QGroupBox { font-weight: bold; }'
        # Top level layout manager for the window.
        win_layout = QVBoxLayout()
        gb_fnt_files = QGroupBox('Font Files')
        gb_fnt_files.setStyleSheet(gb_style)
        grid_f_f = QGridLayout()
        grid_pos = 0

        # Font Files and styles #

        # Create a grid of font names with their respective font style combo boxes
        for i in range(len(self.fnt_styles)):
            self.fnt_file_name_list.append(QLabel('Load font file...'))
            cmb = QComboBox()
            cmb.addItem('')
            cmb.addItems(self.fnt_styles)
            cmb.setEnabled(False)
            cmb.setToolTip('<qt/>If not automatically detected when the font is added, allows you to select what font '
                           'sub-family the font file belongs to')
            self.fnt_sty_combo_list.append(cmb)
            row, col = helper.calc_grid_pos(grid_pos, 2)
            grid_f_f.addWidget(self.fnt_file_name_list[i], row, col)
            grid_pos += 1
            row, col = helper.calc_grid_pos(grid_pos, 2)
            grid_f_f.addWidget(self.fnt_sty_combo_list[i], row, col)
            grid_pos += 1
        grid_f_f.setColumnStretch(0, 1)
        gb_fnt_files.setLayout(grid_f_f)
        win_layout.addWidget(gb_fnt_files)

        # New Font Name #
        gb_fnt_name = QGroupBox('Font Family Name')
        gb_fnt_name.setStyleSheet(gb_style)
        hb_fnt_name = QHBoxLayout()
        self.new_fnt_name = QLineEdit()
        self.new_fnt_name.setToolTip('Enter a name for the modified font.')
        self.new_fnt_name.textEdited[str].connect(self.set_family_name)
        hb_fnt_name.addWidget(self.new_fnt_name)
        gb_fnt_name.setLayout(hb_fnt_name)
        win_layout.addWidget(gb_fnt_name)

        # Options #
        hb_options = QHBoxLayout()

        ## Kerning, Panose, Alt. Name ##
        gb_basic_opt = QGroupBox('Basic Options')
        gb_basic_opt.setStyleSheet(gb_style)
        hb_basic_opt = QHBoxLayout()
        self.basic_opt_list = []
        basic_tooltips = ('<qt/>Some readers and software require \'legacy\', or \'old style\' kerning to be '
                                      'present for kerning to work.',
                          '<qt/>Kobo readers can get confused by PANOSE settings. This option sets all '
                                        'PANOSE information to 0, or \'any\'',
                          '<qt/>Some fonts have issues with renaming. If the generated font does not have '
                                        'the same internal font name as you entered, try enabling this option.')

        for opt, tip in zip(('Legacy Kerning', 'Clear PANOSE', 'Alt. Name'), basic_tooltips):
            self.basic_opt_list.append(QCheckBox(opt))
            self.basic_opt_list[-1].setToolTip(tip)
            hb_basic_opt.addWidget(self.basic_opt_list[-1])

        gb_basic_opt.setLayout(hb_basic_opt)
        hb_options.addWidget(gb_basic_opt)

        ## Hinting ##
        gb_hint_opt = QGroupBox('Hinting Option')
        gb_hint_opt.setStyleSheet(gb_style)
        hb_hint_opt = QHBoxLayout()
        self.hint_opt_list = []
        hint_tooltips = ('<qt/>Keep font hinting as it exists in the orginal font files.<br />'
                         'In most cases, this will look fine on most ebook reading devices.',
                         '<qt/>Some fonts are manually, or "hand" hinted for specific display types (such as LCD). '
                         'These fonts may not look good on other display types such as e-ink, therefore they can be '
                         'removed.',
                         '<qt/>If you don\'t like the original hinting, but you want your font to be hinted, '
                         'this option will auto hint your font.')
        for opt, tip in zip(('Keep Existing', 'Remove Existing', 'AutoHint'), hint_tooltips):
            self.hint_opt_list.append(QRadioButton(opt))
            self.hint_opt_list[-1].setToolTip(tip)
            self.hint_opt_list[-1].toggled.connect(self.set_hint)
            hb_hint_opt.addWidget(self.hint_opt_list[-1])

        self.hint_opt_list[0].setChecked(Qt.Checked)
        gb_hint_opt.setLayout(hb_hint_opt)
        hb_options.addWidget(gb_hint_opt)

        win_layout.addLayout(hb_options)

        ## Darken ##
        gb_dark_opt = QGroupBox('Darken Options')
        gb_dark_opt.setStyleSheet(gb_style)
        hb_dark_opt = QHBoxLayout()
        self.darken_opt = QCheckBox('Darken Font')
        self.darken_opt.setToolTip('<qt/>Darken, or add weight to a font to make it easier to read on e-ink screens.')
        self.darken_opt.toggled.connect(self.set_darken_opt)
        hb_dark_opt.addWidget(self.darken_opt)
        self.mod_bearing_opt = QCheckBox('Modify Bearings')
        self.mod_bearing_opt.setToolTip('<qt/>By default, adding weight to a font increases glyph width. Enable this '
                                        'option to set the glyph width to be roughly equal to the original.<br/><br/>'
                                        'WARNING: This reduces the spacing between glyphs, and should not be used if '
                                        'you have added too much weight.')
        self.mod_bearing_opt.toggled.connect(self.set_mod_bearing)
        self.mod_bearing_opt.setEnabled(False)
        hb_dark_opt.addWidget(self.mod_bearing_opt)

        self.lbl = QLabel('Darken Amount:')
        self.lbl.setEnabled(False)
        hb_dark_opt.addWidget(self.lbl)
        self.darken_amount_opt = QSlider(Qt.Horizontal)
        self.darken_amount_opt.setMinimum(1)
        self.darken_amount_opt.setMaximum(50)
        self.darken_amount_opt.setValue(12)
        self.darken_amount_opt.setEnabled(False)
        self.darken_amount_opt.setToolTip('<qt/>Set the amount to darken a font by. 50 is considered turning a '
                                          'regular weight font into a bold weight font. It is not recommended to '
                                          'darken a font that much however.')
        self.darken_amount_opt.valueChanged[int].connect(self.set_darken_amount)
        hb_dark_opt.addWidget(self.darken_amount_opt)
        self.darken_amount_lab = QLabel()
        self.darken_amount_lab.setText(str(self.darken_amount_opt.value()))
        self.darken_amount_lab.setEnabled(False)
        hb_dark_opt.addWidget(self.darken_amount_lab)
        gb_dark_opt.setLayout(hb_dark_opt)

        win_layout.addWidget(gb_dark_opt)

        # Buttons #
        hb_buttons = QHBoxLayout()
        #hb_buttons.addStretch()
        self.gen_ttf_btn = QPushButton('Generate TTF')
        self.gen_ttf_btn.setEnabled(False)
        self.gen_ttf_btn.setToolTip('<qt/>Generate a new TrueType font based on the options chosen in this program. '
                                    '<br /><br />'
                                    'The new fonts are saved in a directory of your choosing.')
        self.gen_ttf_btn.clicked.connect(self.gen_ttf)
        hb_buttons.addWidget(self.gen_ttf_btn)
        self.load_font_btn = QPushButton('Load Fonts')
        self.load_font_btn.setToolTip('<qt/>Load font files to modify.')
        self.load_font_btn.clicked.connect(self.load_fonts)
        hb_buttons.addWidget(self.load_font_btn)
        self.prog_bar = QProgressBar()
        self.prog_bar.setRange(0,100)
        hb_buttons.addWidget(self.prog_bar)
        win_layout.addLayout(hb_buttons)

        # Output Log #
        gb_log_win = QGroupBox('Log Window')
        gb_log_win.setStyleSheet(gb_style)
        vb_log = QVBoxLayout()
        out_font = QFont('Courier')
        out_font.setStyleHint(QFont.Monospace)
        self.log_win = QTextEdit()
        self.log_win.setAcceptRichText(False)
        self.log_win.setFont(out_font)
        vb_log.addWidget(self.log_win)
        gb_log_win.setLayout(vb_log)
        win_layout.addWidget(gb_log_win)

        # Show Window #
        self.setCentralWidget(QWidget(self))
        self.centralWidget().setLayout(win_layout)
        self.setWindowTitle('Readify Font')

        self.show()

        # Check if fontforge is actually in users PATH. If it isn't, prompt user to provice a location
        self.ff_path = helper.which('fontforge')
        if not self.ff_path:
            self.set_ff_path()

    def set_ff_path(self):
        """
        Let user choose location of fontforge
        :return:
        """
        QMessageBox.warning(self, 'Fontforge Missing!', 'FontForge is not in your PATH! If it is installed, '
                                                      'please locate it now.', QMessageBox.Ok, QMessageBox.Ok)
        path = QFileDialog.getOpenFileName(self, 'Locate FontForge...')
        if path[0]:
            self.ff_path = os.path.normpath(path[0])

    def set_basic_opt(self):
        """
        Handler to set basic options
        :return:
        """
        opt = self.sender()
        if opt.isChecked():
            if 'kerning' in opt.text().lower():
                self.font_info.leg_kern = True
            if 'panose' in opt.text().lower():
                self.font_info.strip_panose = True
            if 'alt' in opt.text().lower():
                self.font_info.name_hack = True
        else:
            if 'kerning' in opt.text().lower():
                self.font_info.leg_kern = False
            if 'panose' in opt.text().lower():
                self.font_info.strip_panose = False
            if 'alt' in opt.text().lower():
                self.font_info.name_hack = False

    def set_family_name(self, name):
        """
        Handler to set name option. Also checks if buttons need enabling
        :param name:
        :return:
        """
        if name:
            if helper.valid_filename(name):
                self.font_info.font_name = name
                if self.font_files:
                    self.gen_ttf_btn.setEnabled(True)
            else:
                self.gen_ttf_btn.setEnabled(False)
        else:
            self.gen_ttf_btn.setEnabled(False)

    def set_darken_amount(self, amount):
        """
        Set Darken amount slider
        :param amount:
        :return:
        """
        self.darken_amount_lab.setText(str(amount))
        self.font_info.add_weight = amount

    def set_hint(self):
        """
        Set hint options
        :return:
        """
        hint = self.sender()
        if hint.isChecked():
            if 'keep' in hint.text().lower():
                self.font_info.change_hint = 'keep'
            elif 'remove' in hint.text().lower():
                self.font_info.change_hint = 'remove'
            elif 'auto' in hint.text().lower():
                self.font_info.change_hint = 'auto'

    def set_darken_opt(self):
        """
        Set darken options
        :return:
        """
        if self.sender().isChecked():
            self.mod_bearing_opt.setEnabled(True)
            self.lbl.setEnabled(True)
            self.darken_amount_lab.setEnabled(True)
            self.darken_amount_opt.setEnabled(True)
            self.set_darken_amount(self.darken_amount_opt.value())
        else:
            self.mod_bearing_opt.setEnabled(False)
            self.lbl.setEnabled(False)
            self.darken_amount_lab.setEnabled(False)
            self.darken_amount_opt.setEnabled(False)
            self.set_darken_amount(0)

    def set_mod_bearing(self):
        """
        Set mod bearing options
        :return:
        """
        if self.mod_bearing_opt.isChecked():
            self.font_info.mod_bearings = True
        else:
            self.font_info.mod_bearings = False

    def load_fonts(self):
        """
        Load fonts from a directory, and sets appropriate options
        :return:
        """
        f_f = QFileDialog.getOpenFileNames(self, 'Load Fonts', '', 'Font Files (*.ttf *.otf)')
        if f_f[0]:
            for f_label, f_style in zip(self.fnt_file_name_list, self.fnt_sty_combo_list):
                f_label.setText('Load font file...')
                f_style.setCurrentIndex(SEL_NONE)
                f_style.setEnabled(False)

            self.font_files = f_f[0]
            f_f_names = []
            for file in self.font_files:
                file = os.path.normpath(file)
                base, fn = os.path.split(file)
                f_f_names.append(fn)

            for f_file, f_label, f_style in zip(f_f_names, self.fnt_file_name_list, self.fnt_sty_combo_list):
                f_label.setText(f_file)
                f_style.setEnabled(True)
                if 'regular' in f_file.lower():
                    f_style.setCurrentIndex(SEL_REGULAR)
                elif 'bold' in f_file.lower() and 'italic' in f_file.lower():
                    f_style.setCurrentIndex(SEL_BOLDITALIC)
                elif 'bold' in f_file.lower():
                    f_style.setCurrentIndex(SEL_BOLD)
                elif 'italic' in f_file.lower():
                    f_style.setCurrentIndex(SEL_ITALIC)

            if self.new_fnt_name.text():
                self.gen_ttf_btn.setEnabled(True)

    def read_proc_output(self):
        """
        Read any stdout data available from the process and displays it in the output log window.
        :return:
        """
        if sys.version_info.major == 2:
            output = unicode(self.cli_process.readAllStandardOutput(), encoding=sys.getdefaultencoding())
        else:
            output = str(self.cli_process.readAllStandardOutput(), encoding=sys.getdefaultencoding())
        self.log_win.append(output)

    def manage_proc(self):
        """
        Manage the progress bar
        :return:
        """
        proc = self.sender()
        if proc.state() == QProcess.Running:
            self.prog_bar.setRange(0,0)
        if proc.state() == QProcess.NotRunning:
            self.prog_bar.setRange(0,100)
            self.prog_bar.setValue(100)

    def gen_ttf(self):
        """
        Generate modified TrueType font files, by calling the CLI script with the appropriate arguments.
        :param prev:
        :return:
        """
        self.log_win.clear()
        if not self.ff_path:
            self.set_ff_path()
        if self.ff_path:
            if not self.font_info.out_dir:
                save_dir = os.path.normpath(QFileDialog.getExistingDirectory(self, 'Select save directory...',
                                                                             options=QFileDialog.ShowDirsOnly))
                if save_dir == '.' or save_dir == '':
                    return
                else:
                    self.font_info.out_dir = save_dir
            else:
                save_dir = os.path.normpath(QFileDialog.getExistingDirectory(self, 'Select Save directory...',
                                                                             self.font_info.out_dir,
                                                                             options=QFileDialog.ShowDirsOnly))
                if save_dir == '.' or save_dir == '':
                    return
                else:
                    self.font_info.out_dir = save_dir

            for file, style in zip(self.font_files, self.fnt_sty_combo_list):
                if style.currentIndex() == SEL_REGULAR:
                    self.font_info.font_file_reg = file
                elif style.currentIndex() == SEL_BOLDITALIC:
                    self.font_info.font_file_bi = file
                elif style.currentIndex() == SEL_BOLD:
                    self.font_info.font_file_bd = file
                elif style.currentIndex() == SEL_ITALIC:
                    self.font_info.font_file_it = file

            cli_opt_list = self.font_info.gen_cli_command()
            self.cli_process.start(self.ff_path, cli_opt_list)

    def closeEvent(self, event):
        """
        Cleaning up...
        :param event:
        :return:
        """
        self.cli_process.close()
        event.accept()

def main():
    app = QApplication(sys.argv)
    rf = RF_Qt()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
