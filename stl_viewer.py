import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QAction,
    QFileDialog, QMessageBox, QDockWidget, QListWidget, QPushButton, QColorDialog,
    QSlider, QCheckBox, QComboBox, QLabel, QGroupBox, QFormLayout, QFrame,
    QProgressDialog
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon
import pyvista as pv
from pyvistaqt import QtInteractor

MAX_RECENT_FILES = 5

# main class
class AdvancedSTLViewer(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # settings
        self.settings = QSettings("MyCompany", "STLViewer")

        # window
        self.setWindowTitle("STL Viewer")
        self.setGeometry(100, 100, 1600, 900)
        self.restoreGeometry(self.settings.value("geometry", self.saveGeometry()))

        # variables
        self.current_mesh_actor = None
        self.current_mesh = None
        self.file_path = None
        self.recent_file_actions = []
        self.axes_actor = None

        # layout
        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = QHBoxLayout(self.main_widget)

        # plotter
        self.plotter_frame = QFrame()
        self.plotter_layout = QVBoxLayout(self.plotter_frame)
        self.plotter = QtInteractor(self.plotter_frame)
        self.plotter_layout.addWidget(self.plotter.interactor)
        self.main_layout.addWidget(self.plotter_frame, 1)

        # ui stuff
        self.create_actions()
        self.create_menus()
        self.create_toolbar()
        self.create_status_bar()
        self.create_docks()
        
        # drag drop
        self.setAcceptDrops(True)

        # scene
        self.setup_initial_scene()
        self.update_recent_files_menu()

    # actions
    def create_actions(self):
        self.open_action = QAction(QIcon.fromTheme("document-open"), "&Open...", self,
                                   shortcut="Ctrl+O", statusTip="Open an STL file", triggered=self.open_file_dialog)
        self.screenshot_action = QAction(QIcon.fromTheme("camera-photo"), "&Save Screenshot...", self,
                                         shortcut="Ctrl+S", statusTip="Save the current view as an image", triggered=self.take_screenshot)
        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "&Exit", self,
                                   shortcut="Ctrl+Q", statusTip="Exit the application", triggered=self.close)

        self.reset_view_action = QAction(QIcon.fromTheme("zoom-fit-best"), "Reset View", self,
                                         statusTip="Reset camera to fit the model", triggered=self.reset_view)
        self.view_iso_action = QAction(QIcon.fromTheme("camera-view"), "Isometric", self,
                                       statusTip="Set isometric camera view", triggered=lambda: self.set_view('iso'))
        self.view_xy_action = QAction(QIcon.fromTheme("go-up"), "Top (+Z)", self,
                                      statusTip="View from the top", triggered=lambda: self.set_view('xy'))
        self.view_xz_action = QAction(QIcon.fromTheme("go-previous"), "Front (+Y)", self,
                                      statusTip="View from the front", triggered=lambda: self.set_view('xz'))
        self.view_yz_action = QAction(QIcon.fromTheme("go-next"), "Side (+X)", self,
                                      statusTip="View from the side", triggered=lambda: self.set_view('yz'))

        self.color_by_height_action = QAction("Color by Height (Z-axis)", self,
                                              statusTip="Apply a colormap based on Z-axis coordinates", triggered=self.apply_color_by_height)

        for i in range(MAX_RECENT_FILES):
            action = QAction(self, visible=False, triggered=self.open_recent_file)
            self.recent_file_actions.append(action)

    # menus
    def create_menus(self):
        self.file_menu = self.menuBar().addMenu("&File")
        self.file_menu.addAction(self.open_action)
        self.open_recent_menu = self.file_menu.addMenu("Open Recent")
        for i in range(MAX_RECENT_FILES):
            self.open_recent_menu.addAction(self.recent_file_actions[i])
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.screenshot_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)

        self.view_menu = self.menuBar().addMenu("&View")
        self.view_menu.addAction(self.reset_view_action)
        self.view_menu.addSeparator()
        self.view_menu.addAction(self.view_iso_action)
        self.view_menu.addAction(self.view_xy_action)
        self.view_menu.addAction(self.view_xz_action)
        self.view_menu.addAction(self.view_yz_action)

        self.tools_menu = self.menuBar().addMenu("&Tools")
        self.tools_menu.addAction(self.color_by_height_action)

    # toolbar
    def create_toolbar(self):
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.addAction(self.open_action)
        toolbar.addSeparator()
        toolbar.addAction(self.reset_view_action)
        toolbar.addAction(self.view_iso_action)
        toolbar.addAction(self.view_xy_action)
        toolbar.addAction(self.view_xz_action)
        toolbar.addAction(self.view_yz_action)
        toolbar.addSeparator()
        toolbar.addAction(self.screenshot_action)

    # status bar
    def create_status_bar(self):
        self.statusBar().showMessage("Ready. Open an STL file to begin.")

    # docks
    def create_docks(self):
        properties_dock = QDockWidget("Properties", self)
        properties_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, properties_dock)
        
        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.setAlignment(Qt.AlignTop)
        properties_dock.setWidget(dock_widget)

        mesh_group = QGroupBox("Mesh Display")
        mesh_layout = QFormLayout()

        self.mesh_color_btn = QPushButton("Change Color")
        self.mesh_color_btn.clicked.connect(self.change_mesh_color)
        mesh_layout.addRow("Color:", self.mesh_color_btn)

        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_slider.setValue(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        mesh_layout.addRow("Opacity:", self.opacity_slider)

        self.representation_combo = QComboBox()
        self.representation_combo.addItems(["Surface", "Wireframe", "Points"])
        self.representation_combo.currentIndexChanged.connect(self.change_representation)
        mesh_layout.addRow("Style:", self.representation_combo)
        
        self.show_edges_check = QCheckBox("Show Edges")
        self.show_edges_check.toggled.connect(self.toggle_edges)
        mesh_layout.addRow(self.show_edges_check)

        self.smooth_shading_check = QCheckBox("Smooth Shading")
        self.smooth_shading_check.toggled.connect(self.toggle_smooth_shading)
        mesh_layout.addRow(self.smooth_shading_check)

        mesh_group.setLayout(mesh_layout)
        dock_layout.addWidget(mesh_group)

        scene_group = QGroupBox("Scene")
        scene_layout = QFormLayout()

        self.bg_color_btn = QPushButton("Change Background")
        self.bg_color_btn.clicked.connect(self.change_background_color)
        scene_layout.addRow(self.bg_color_btn)

        self.grid_check = QCheckBox("Show Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self.toggle_grid)
        scene_layout.addRow(self.grid_check)
        
        self.axes_check = QCheckBox("Show Axes")
        self.axes_check.setChecked(True)
        self.axes_check.toggled.connect(self.toggle_axes_visibility)
        scene_layout.addRow(self.axes_check)

        scene_group.setLayout(scene_layout)
        dock_layout.addWidget(scene_group)

        lighting_group = QGroupBox("Lighting")
        lighting_layout = QFormLayout()
        
        self.ambient_slider = QSlider(Qt.Horizontal)
        self.ambient_slider.setRange(0, 100)
        self.ambient_slider.setValue(20)
        self.ambient_slider.valueChanged.connect(self.update_lighting)
        lighting_layout.addRow("Ambient:", self.ambient_slider)

        self.diffuse_slider = QSlider(Qt.Horizontal)
        self.diffuse_slider.setRange(0, 100)
        self.diffuse_slider.setValue(80)
        self.diffuse_slider.valueChanged.connect(self.update_lighting)
        lighting_layout.addRow("Diffuse:", self.diffuse_slider)

        self.specular_slider = QSlider(Qt.Horizontal)
        self.specular_slider.setRange(0, 100)
        self.specular_slider.setValue(50)
        self.specular_slider.valueChanged.connect(self.update_lighting)
        lighting_layout.addRow("Specular:", self.specular_slider)

        lighting_group.setLayout(lighting_layout)
        dock_layout.addWidget(lighting_group)

        dock_layout.addStretch(1)
        credit_label = QLabel("Made by Atharv Gogia")
        credit_label.setAlignment(Qt.AlignCenter)
        credit_label.setStyleSheet("font-style: italic; color: gray;")
        dock_layout.addWidget(credit_label)

        info_dock = QDockWidget("Model Information", self)
        info_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, info_dock)

        info_widget = QWidget()
        info_layout = QFormLayout(info_widget)
        
        self.filename_label = QLabel("N/A")
        self.points_label = QLabel("N/A")
        self.cells_label = QLabel("N/A")
        self.bounds_label = QLabel("N/A")
        self.surface_area_label = QLabel("N/A")
        self.volume_label = QLabel("N/A")

        info_layout.addRow("<b>File:</b>", self.filename_label)
        info_layout.addRow("<b>Points:</b>", self.points_label)
        info_layout.addRow("<b>Triangles:</b>", self.cells_label)
        info_layout.addRow("<b>Bounds:</b>", self.bounds_label)
        info_layout.addRow("<b>Surface Area:</b>", self.surface_area_label)
        info_layout.addRow("<b>Volume:</b>", self.volume_label)
        
        info_dock.setWidget(info_widget)
        
        self.set_controls_enabled(False)

    # scene setup
    def setup_initial_scene(self):
        self.plotter.add_text("Open an STL file to begin (Ctrl+O)", font_size=12, position='upper_left')
        self.plotter.enable_lightkit()
        self.plotter.show_grid()
        self.axes_actor = self.plotter.add_axes()
        self.plotter.set_background('darkgray')

    # open dialog
    def open_file_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open STL File", "", "STL Files (*.stl *.STL)")
        if file_path:
            self.load_stl(file_path)
            
    # load stl
    def load_stl(self, file_path):
        progress = QProgressDialog("Loading file...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setCancelButton(None) 
        progress.show()
        QApplication.processEvents()

        try:
            self.current_mesh = pv.read(file_path)
            self.file_path = file_path
            
            self.plotter.clear()
            self.plotter.clear_actors()
            self.plotter.enable_lightkit()

            self.current_mesh_actor = self.plotter.add_mesh(
                self.current_mesh,
                name='primary_mesh',
                show_edges=self.show_edges_check.isChecked(),
                lighting=True,
                specular=self.specular_slider.value()/100.0,
                diffuse=self.diffuse_slider.value()/100.0,
                ambient=self.ambient_slider.value()/100.0,
                smooth_shading=self.smooth_shading_check.isChecked()
            )

            if self.grid_check.isChecked(): self.plotter.show_grid()
            self.axes_actor = self.plotter.add_axes()
            self.toggle_axes_visibility(self.axes_check.isChecked())
            
            self.reset_view()
            self.update_info_panel()
            self.set_controls_enabled(True)
            self.setWindowTitle(f"STL Viewer - {os.path.basename(file_path)}")
            self.statusBar().showMessage(f"Successfully loaded {os.path.basename(file_path)}", 5000)
            self.add_to_recent_files(file_path)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load the STL file.\n\nError: {e}")
            self.statusBar().showMessage("Failed to load file.", 5000)
        finally:
            progress.close()

    # ui controls
    def set_controls_enabled(self, enabled):
        self.mesh_color_btn.setEnabled(enabled)
        self.opacity_slider.setEnabled(enabled)
        self.representation_combo.setEnabled(enabled)
        self.show_edges_check.setEnabled(enabled)
        self.smooth_shading_check.setEnabled(enabled)
        self.ambient_slider.setEnabled(enabled)
        self.diffuse_slider.setEnabled(enabled)
        self.specular_slider.setEnabled(enabled)
        
        for action in [self.screenshot_action, self.reset_view_action, self.view_iso_action, 
                       self.view_xy_action, self.view_xz_action, self.view_yz_action, 
                       self.color_by_height_action]:
            action.setEnabled(enabled)

    # info panel
    def update_info_panel(self):
        if self.current_mesh:
            bounds = self.current_mesh.bounds
            self.filename_label.setText(f"<i>{os.path.basename(self.file_path)}</i>")
            self.points_label.setText(f"{self.current_mesh.n_points:,}")
            self.cells_label.setText(f"{self.current_mesh.n_cells:,}")
            self.bounds_label.setText(f"X: {bounds[0]:.2f} to {bounds[1]:.2f}<br>"
                                      f"Y: {bounds[2]:.2f} to {bounds[3]:.2f}<br>"
                                      f"Z: {bounds[4]:.2f} to {bounds[5]:.2f}")
            self.surface_area_label.setText(f"{self.current_mesh.area:.2f}")
            self.volume_label.setText(f"{self.current_mesh.volume:.2f}")

    # mesh color
    def change_mesh_color(self):
        if self.current_mesh_actor:
            try:
                self.plotter.remove_scalar_bar()
            except (IndexError, StopIteration):
                pass
            
            color = QColorDialog.getColor()
            if color.isValid():
                self.current_mesh_actor.prop.color = color.name()
                self.current_mesh_actor.mapper.scalar_visibility = False

    # bg color
    def change_background_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.plotter.set_background(color.name())

    # opacity
    def change_opacity(self, value):
        if self.current_mesh_actor:
            opacity = value / 100.0
            self.current_mesh_actor.prop.opacity = opacity

    # representation
    def change_representation(self, index):
        if self.current_mesh_actor:
            styles = ['surface', 'wireframe', 'points']
            self.current_mesh_actor.prop.style = styles[index]
    
    # edges
    def toggle_edges(self, state):
        if self.current_mesh_actor:
            self.current_mesh_actor.prop.show_edges = state
            
    # grid
    def toggle_grid(self, state):
        if state:
            self.plotter.show_grid()
        else:
            self.plotter.hide_grid()
    
    # axes visibility
    def toggle_axes_visibility(self, state):
        if self.axes_actor:
            self.axes_actor.SetVisibility(state)

    # shading
    def toggle_smooth_shading(self, state):
        if self.current_mesh_actor:
            if state:
                self.current_mesh_actor.prop.interpolation = 'gouraud'
            else:
                self.current_mesh_actor.prop.interpolation = 'flat'

    # lighting
    def update_lighting(self):
        if self.current_mesh_actor:
            self.current_mesh_actor.prop.ambient = self.ambient_slider.value() / 100.0
            self.current_mesh_actor.prop.diffuse = self.diffuse_slider.value() / 100.0
            self.current_mesh_actor.prop.specular = self.specular_slider.value() / 100.0

    # reset view
    def reset_view(self):
        self.plotter.reset_camera()
        self.statusBar().showMessage("Camera view reset", 2000)

    # set view
    def set_view(self, view):
        if self.current_mesh:
            self.plotter.camera_position = view
            self.reset_view()

    # screenshot
    def take_screenshot(self):
        if self.current_mesh:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", "", "PNG Image (*.png)")
            if file_path:
                self.plotter.screenshot(file_path)
                self.statusBar().showMessage(f"Screenshot saved to {file_path}", 5000)

    # recent files
    def add_to_recent_files(self, file_path):
        files = self.settings.value("recent_files", [], type=list)
        try:
            files.remove(file_path)
        except ValueError:
            pass
        files.insert(0, file_path)
        del files[MAX_RECENT_FILES:]
        self.settings.setValue("recent_files", files)
        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        files = self.settings.value("recent_files", [], type=list)
        num_recent_files = min(len(files), MAX_RECENT_FILES)

        for i in range(num_recent_files):
            text = f"&{i + 1} {os.path.basename(files[i])}"
            self.recent_file_actions[i].setText(text)
            self.recent_file_actions[i].setData(files[i])
            self.recent_file_actions[i].setVisible(True)

        for i in range(num_recent_files, MAX_RECENT_FILES):
            self.recent_file_actions[i].setVisible(False)

    def open_recent_file(self):
        action = self.sender()
        if action:
            self.load_stl(action.data())

    # tools
    def apply_color_by_height(self):
        if self.current_mesh:
            self.plotter.add_mesh(
                self.current_mesh,
                name='primary_mesh',
                scalars=self.current_mesh.points[:, 2],
                scalar_bar_args={'title': 'Z-Height'},
                cmap='viridis',
                show_edges=self.show_edges_check.isChecked() 
            )
            # mapper using scalars
            if self.current_mesh_actor:
                self.current_mesh_actor.mapper.scalar_visibility = True
            self.statusBar().showMessage("Applied color map by height.", 3000)

    # drag event
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    # drop event
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            file_path = files[0]
            if file_path.lower().endswith('.stl'):
                self.load_stl(file_path)
            else:
                self.statusBar().showMessage("Error: Can only accept .stl files.", 5000)
    
    # close event
    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

# run it
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = AdvancedSTLViewer()
    window.show()
    sys.exit(app.exec_())

