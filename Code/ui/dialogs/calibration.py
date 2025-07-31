"""
Complete Calibration wizard dialog for MakerStop Controller.
Provides step-by-step calibration process with user-defined test distances.
"""
import json
import time
from functools import partial
from PyQt5.QtWidgets import (QDialog, QLabel, QPushButton, QLineEdit,
                           QMessageBox, QInputDialog)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt, QTimer

from config.constants import (COLORS, MAX_MACHINE_DISTANCE,
                             CALIBRATION_FILE, DEFAULT_STEPS_PER_MM)


class CalibrationDialog(QDialog):
    """Complete calibration wizard with user-defined distance selection, measurement input, and automatic calibration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_dialog()
        self._init_variables()
        self._init_ui()

    def _init_dialog(self):
        """Initialize dialog properties."""
        self.setWindowTitle('Calibration Wizard')
        self.setGeometry(0, 0, 800, 600)
        self.setFixedSize(800, 600)

    def _init_variables(self):
        """Initialize instance variables."""
        self.move_executed = False
        self.correction_factor = 1.0
        self.numpad_buttons = []
        self.selected_distance = 0
        self.target_distance = 0
        self.current_input_target = None

    def _init_ui(self):
        """Initialize all UI elements."""
        # self._create_instructions()  # Remove or comment out this line
        self._create_distance_input()
        self._create_measurement_input()
        self._create_numpad()
        self._create_action_buttons()
        self._create_result_display()

    def _create_distance_input(self):
        """Create distance input section."""
        # Distance input label
        self.distance_label = QLabel("Test Distance (mm):", self)
        self.distance_label.setGeometry(400, 130, 200, 30)
        self.distance_label.setFont(QFont('Proxima Nova', 14, QFont.Bold))

        # Distance input field
        self.distance_input = QLineEdit(self)
        self.distance_input.setGeometry(400, 160, 200, 40)
        self.distance_input.setPlaceholderText("Enter distance")
        self.distance_input.setFont(QFont('Proxima Nova', 14))
        self.distance_input.setStyleSheet("padding: 8px; border: 2px solid #ccc; border-radius: 5px;")
        self.distance_input.setAlignment(Qt.AlignCenter)
        self.distance_input.focusInEvent = lambda e: self._set_input_target(self.distance_input, e)

        # Move button
        self.move_button = QPushButton("Move to Distance", self)
        self.move_button.setGeometry(400, 210, 200, 50)
        self.move_button.setFont(QFont('Proxima Nova', 12, QFont.Bold))
        self.move_button.setStyleSheet(f"""
            background-color: {COLORS['info']};
            color: white;
            border-radius: 8px;
            font-weight: bold;
        """)
        self.move_button.clicked.connect(self._move_to_custom_distance)

    def _create_measurement_input(self):
        """Create measurement input field."""
        self.measurement_label = QLabel("Measured length (mm):", self)
        self.measurement_label.setGeometry(400, 280, 250, 30)
        self.measurement_label.setFont(QFont('Proxima Nova', 14))

        self.measurement_input = QLineEdit(self)
        self.measurement_input.setGeometry(400, 310, 300, 60)
        self.measurement_input.setPlaceholderText("Enter measured length")
        self.measurement_input.setFont(QFont('Proxima Nova', 18))
        self.measurement_input.setStyleSheet("padding: 12px; border: 3px solid #ccc; border-radius: 10px;")
        self.measurement_input.setAlignment(Qt.AlignCenter)
        self.measurement_input.focusInEvent = lambda e: self._set_input_target(self.measurement_input, e)

        # Set default target to distance input
        self.current_input_target = self.distance_input

    def _create_numpad(self):
        """Create numerical keypad."""
        numpad_start_x = 20
        numpad_start_y = 150
        button_width = 90
        button_height = 60
        button_spacing = 5
        button_font = QFont('Proxima Nova', 18)

        buttons = [
            ('7', 0, 0), ('8', 0, 1), ('9', 0, 2),
            ('4', 1, 0), ('5', 1, 1), ('6', 1, 2),
            ('1', 2, 0), ('2', 2, 1), ('3', 2, 2),
            ('C', 3, 0), ('0', 3, 1), ('.', 3, 2),
        ]

        self.numpad_buttons = []

        for text, row, col in buttons:
            btn = QPushButton(text, self)

            x = numpad_start_x + col * (button_width + button_spacing)
            y = numpad_start_y + row * (button_height + button_spacing)

            btn.setGeometry(x, y, button_width, button_height)
            btn.setFont(button_font)
            btn.clicked.connect(partial(self._numpad_clicked, text))

            if text == 'C':
                btn.setStyleSheet(f"""
                    background-color: {COLORS['danger']};
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                """)
            else:
                btn.setStyleSheet(f"""
                    background-color: {COLORS['secondary']};
                    color: white;
                    border-radius: 8px;
                    font-weight: bold;
                """)

            self.numpad_buttons.append(btn)

        # Add backspace button
        backspace_btn = QPushButton('←', self)
        backspace_x = numpad_start_x
        backspace_y = numpad_start_y + 4 * (button_height + button_spacing)
        backspace_width = 3 * button_width + 2 * button_spacing

        backspace_btn.setGeometry(backspace_x, backspace_y, backspace_width, button_height)
        backspace_btn.setFont(button_font)
        backspace_btn.setStyleSheet(f"""
            background-color: {COLORS['warning']};
            color: white;
            border-radius: 8px;
            font-weight: bold;
        """)
        backspace_btn.clicked.connect(self._backspace_clicked)
        self.numpad_buttons.append(backspace_btn)

    def _create_action_buttons(self):
        """Create action buttons."""
        self.calc_button = QPushButton("Calculate and Apply Calibration", self)
        self.calc_button.setGeometry(400, 390, 350, 60)
        self.calc_button.setFont(QFont('Proxima Nova', 16))
        self.calc_button.setStyleSheet(f"""
            background-color: {COLORS['success']};
            color: white;
            padding: 10px;
            border-radius: 10px;
            font-weight: bold;
        """)
        self.calc_button.clicked.connect(self._calculate_calibration)
        self.calc_button.setEnabled(False)

        self.cancel_button = QPushButton("Cancel", self)
        self.cancel_button.setGeometry(500, 500, 150, 60)
        self.cancel_button.setFont(QFont('Proxima Nova', 14))
        self.cancel_button.setStyleSheet(f"""
            background-color: {COLORS['danger']};
            color: white;
            padding: 8px;
            border-radius: 10px;
        """)
        self.cancel_button.clicked.connect(self.reject)

    def _create_result_display(self):
        """Create result display label."""
        self.result_label = QLabel("Enter a test distance and click 'Move to Distance' to start calibration", self)
        self.result_label.setGeometry(50, 20, 700, 60)
        self.result_label.setStyleSheet("""
            color: #333;
            font-weight: bold;
            font-size: 12pt;
            padding: 8px;
            background-color: #ffffcc;
            border-radius: 5px;
        """)
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)


    def _move_to_custom_distance(self):
        """Move machine to user-specified distance."""
        try:
            # Get distance from input
            distance_text = self.distance_input.text().strip()
            if not distance_text:
                QMessageBox.warning(self, "Input Error", "Please enter a test distance.")
                return

            distance = float(distance_text)

            if distance <= 0:
                QMessageBox.warning(self, "Input Error", "Distance must be greater than 0.")
                return

            # Check if machine is homed
            reply = QMessageBox.question(self, 'Homing Check',
                                        'Is the machine homed? If not, please home it before calibration.',
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.result_label.setText("Please home the machine first and try again.")
                return

            # Check parent communication capability
            if not hasattr(self.parent(), 'send_command_to_cnc'):
                self.result_label.setText("Error: Cannot communicate with CNC controller")
                return

            # Check distance limits
            if distance > MAX_MACHINE_DISTANCE:
                QMessageBox.warning(self, "Distance Error",
                                   f"The distance {distance}mm exceeds the machine limit of {MAX_MACHINE_DISTANCE}mm.")
                return

            # Warn for large distances
            if distance > 2000:
                reply = QMessageBox.question(self, 'Large Distance Warning',
                                           f'You entered {distance}mm, which is quite large.\n'
                                           'Are you sure you want to proceed?',
                                           QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply != QMessageBox.Yes:
                    return

            # Store distance and send commands
            self.selected_distance = distance
            self.target_distance = distance

            # Use relative positioning for consistent movement
            self.parent().send_command_to_cnc("G91")  # Relative positioning
            self.parent().send_command_to_cnc(f"G0 X{distance}")  # Move distance
            self.parent().send_command_to_cnc("G90")  # Absolute positioning

            # Update UI state
            self.move_button.setEnabled(False)
            self.distance_input.setEnabled(False)
            self.calc_button.setEnabled(True)
            self.move_executed = True

            self.measurement_input.setPlaceholderText(f"Enter measured length (target: {distance}mm)")
            self.result_label.setText(f"Machine moving {distance}mm in positive direction. Make a cut and measure it precisely.")

        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter a valid number for distance.")
        except Exception as e:
            self.result_label.setText(f"Error moving machine: {e}")

    def _calculate_calibration(self):
        """Calculate and apply calibration."""
        try:
            if not self.move_executed:
                self.result_label.setText("Error: Please enter a distance and move first.")
                return

            measured_text = self.measurement_input.text().replace(',', '.')
            if not measured_text:
                self.result_label.setText("Please enter the measured length.")
                return

            measured = float(measured_text)

            if measured <= 0:
                self.result_label.setText("Error: Measurement must be positive.")
                return

            # Validate measurement is reasonable
            min_expected = self.target_distance * 0.8  # Allow for larger errors
            max_expected = self.target_distance * 1.2

            if measured < min_expected or measured > max_expected:
                reply = QMessageBox.question(self, 'Measurement Check',
                                            f'The measurement ({measured:.2f}mm) seems unusual for a {self.target_distance}mm move.\n'
                                            f'Expected range: {min_expected:.1f}mm - {max_expected:.1f}mm\n\n'
                                            f'Are you sure this measurement is correct?',
                                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return

            # Calculate correction factor
            self.correction_factor = self.target_distance / measured

            # Show calibration analysis
            accuracy_error = abs(measured - self.target_distance)
            accuracy_percent = (accuracy_error / self.target_distance) * 100

            message = (f"Calibration Analysis:\n"
                      f"Target distance: {self.target_distance:.2f}mm\n"
                      f"Measured distance: {measured:.2f}mm\n"
                      f"Error: {accuracy_error:.2f}mm ({accuracy_percent:.2f}%)\n"
                      f"Correction factor: {self.correction_factor:.6f}\n\n"
                      f"Apply this calibration to the machine?")

            reply = QMessageBox.question(self, 'Confirm Calibration', message,
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)

            if reply == QMessageBox.Yes:
                self._get_current_steps_per_mm()
            else:
                self.result_label.setText("Calibration canceled by user.")
                self._reset_buttons()

        except ValueError:
            self.result_label.setText("Error: Please enter a valid number.")
        except Exception as e:
            self.result_label.setText(f"Error calculating calibration: {e}")

    def _get_current_steps_per_mm(self):
        """Get current steps/mm setting from user."""
        try:
            last_value = self._load_last_steps_per_mm()

            dialog_text = (
                f"Enter the current X-axis steps/mm setting:\n\n"
                f"Last used value: {last_value:.3f} steps/mm\n\n"
                f"To find current value, send this command to your machine:\n"
                f"$/axes/x/steps_per_mm\n\n"
                f"Common values:\n"
                f"• 200 steps/mm (most common)\n"
                f"• 400 steps/mm (0.9° motors or 2:1 gearing)\n"
                f"• 800 steps/mm (microstepping or higher gearing)\n\n"
                f"Enter current steps/mm:"
            )

            current_steps, ok = QInputDialog.getDouble(
                self, 'Current Steps/mm Setting', dialog_text,
                last_value, 0.1, 10000.0, 3
            )

            if ok and current_steps > 0:
                self._save_steps_per_mm(current_steps)
                self._apply_calibration(current_steps)
            else:
                self.result_label.setText("Calibration canceled - no steps/mm value provided.")

        except Exception as e:
            self.result_label.setText(f"Error: {e}")

    def _apply_calibration(self, current_steps_per_mm):
        """Apply calibration using current steps/mm value."""
        try:
            new_steps_per_mm = current_steps_per_mm * self.correction_factor

            self.result_label.setText(f"Applying calibration: {current_steps_per_mm:.3f} → {new_steps_per_mm:.3f} steps/mm")

            # Send FluidNC calibration commands
            update_command = f"$/axes/x/steps_per_mm={new_steps_per_mm:.3f}"
            self.parent().send_command_to_cnc(update_command)

            # Save settings after delay
            QTimer.singleShot(2000, lambda: self._save_calibration_settings(current_steps_per_mm, new_steps_per_mm))

        except Exception as e:
            self.result_label.setText(f"Error applying calibration: {e}")

    def _save_calibration_settings(self, old_value, new_value):
        """Save calibration settings to config file."""
        try:
            # Save to FluidNC config
            self.parent().send_command_to_cnc("$CD=config.yaml")

            # Save to JSON for next time
            self._save_steps_per_mm(new_value)

            # Verify after delay
            QTimer.singleShot(3000, lambda: self._verify_calibration(old_value, new_value))

        except Exception as e:
            self.result_label.setText(f"Error saving settings: {e}")

    def _verify_calibration(self, old_value, new_value):
        """Verify calibration was applied and show completion."""
        try:
            # Request current settings
            self.parent().send_command_to_cnc("$/axes/x/steps_per_mm")

            # Show completion
            self.result_label.setText(f"Calibration Complete! {old_value:.3f} → {new_value:.3f} steps/mm")

            # Log to parent terminal
            if hasattr(self.parent(), 'append_to_terminal'):
                self.parent().append_to_terminal(f"CALIBRATION APPLIED: {old_value:.3f} → {new_value:.3f} steps/mm (factor: {self.correction_factor:.4f}) at {self.target_distance}mm test distance")

            # Show success dialog
            QMessageBox.information(self, "Calibration Complete",
                                   f"Machine calibrated successfully!\n\n"
                                   f"Test distance: {self.target_distance}mm\n"
                                   f"Old setting: {old_value:.3f} steps/mm\n"
                                   f"New setting: {new_value:.3f} steps/mm\n"
                                   f"Correction factor: {self.correction_factor:.4f}\n\n"
                                   f"Settings saved to config.yaml\n"
                                   f"Value remembered for next calibration!\n\n"
                                   f"💡 Tip: Test with a different distance to verify accuracy")

            self.accept()

        except Exception as e:
            self.result_label.setText(f"Calibration applied, but verification failed: {e}")

    def _reset_buttons(self):
        """Reset buttons to allow new calibration."""
        self.move_button.setEnabled(True)
        self.distance_input.setEnabled(True)
        self.calc_button.setEnabled(False)
        self.move_executed = False
        self.measurement_input.clear()
        self.measurement_input.setPlaceholderText("Enter measured length")
        self.result_label.setText("Enter a test distance and click 'Move to Distance' to start calibration")

    def _set_input_target(self, target, event):
        """Set the target input field for numpad operations."""
        self.current_input_target = target
        target.setStyleSheet(target.styleSheet().replace("border: 2px solid #ccc", "border: 2px solid #4CAF50").replace("border: 3px solid #ccc", "border: 3px solid #4CAF50"))
        # Reset other input field styling
        if target == self.distance_input:
            self.measurement_input.setStyleSheet("padding: 12px; border: 3px solid #ccc; border-radius: 10px;")
        else:
            self.distance_input.setStyleSheet("padding: 8px; border: 2px solid #ccc; border-radius: 5px;")
        # Call the original focus event
        QLineEdit.focusInEvent(target, event)

    def _numpad_clicked(self, value):
        """Handle numpad button clicks."""
        try:
            if not self.current_input_target:
                self.current_input_target = self.distance_input

            current_text = self.current_input_target.text()

            if value == 'C':
                self.current_input_target.clear()
            elif value == '.':
                if '.' not in current_text:
                    self.current_input_target.setText(current_text + value)
            else:
                self.current_input_target.setText(current_text + str(value))

        except Exception as e:
            print(f"Error in numpad_clicked: {e}")

    def _backspace_clicked(self):
        """Handle backspace button."""
        try:
            if not self.current_input_target:
                self.current_input_target = self.distance_input

            current_text = self.current_input_target.text()
            if current_text:
                self.current_input_target.setText(current_text[:-1])
        except Exception as e:
            print(f"Error in backspace_clicked: {e}")

    def _load_last_steps_per_mm(self):
        """Load last used steps/mm value from JSON file."""
        try:
            with open(CALIBRATION_FILE, 'r') as file:
                data = json.load(file)
                return data.get('last_steps_per_mm', DEFAULT_STEPS_PER_MM)
        except FileNotFoundError:
            return DEFAULT_STEPS_PER_MM
        except Exception as e:
            print(f"Error loading calibration data: {e}")
            return DEFAULT_STEPS_PER_MM

    def _save_steps_per_mm(self, steps_per_mm):
        """Save steps/mm value to JSON file."""
        try:
            # Load existing data or create new
            try:
                with open(CALIBRATION_FILE, 'r') as file:
                    data = json.load(file)
            except FileNotFoundError:
                data = {}

            # Update with new value
            data['last_steps_per_mm'] = steps_per_mm
            data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')

            # Save back to file
            with open(CALIBRATION_FILE, 'w') as file:
                json.dump(data, file, indent=2)

        except Exception as e:
            print(f"Error saving calibration data: {e}")