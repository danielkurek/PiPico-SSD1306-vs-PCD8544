import pcd8544_fb, ssd1306
from machine import Pin, SPI, I2C
import time, math
import im9x14u
from writer import Writer
import framebuf

# TODO:
# Images

class Button:
    debounce_time = 20
    
    def __init__(self, pin_no):
        self.pin = Pin(pin_no, Pin.IN, Pin.PULL_DOWN)
        self.pressed = 0
        self.state = 0 # 0 - UP, 1 - DEBOUNCING, 2 - DOWN
    def isPressed(self, now):
        btn_val = self.pin.value()
        if btn_val == 0:
            self.state = 0
            return False
        
        if self.state == 0: # state is UP
            self.pressed = now
            self.state = 1 # DEBOUNCING
            return False
        if self.state == 1: # DEBOUNCING
            if time.ticks_diff(now, self.pressed) > Button.debounce_time:
                self.state = 2 # DOWN
                return True
            return False
        if self.state == 2:
            return False
        
        return False

class Screen:
    def __init__(self, display, is_active = False, return_screen=None):
        self.display = display
        self.is_active = is_active
        self.return_screen = return_screen if return_screen != None else self
    
    def activate(self):
        self.is_active = True
        self.draw()

    def deactivate(self):
        self.is_active = False

    def draw(self):
        pass

    def up(self):
        pass

    def down(self):
        pass

    def ok(self):
        return self.return_screen
    
    def tick(self, now):
        pass

class Menu(Screen):
    def __init__(self, display, is_active=False, return_screen=None, items=None, item_height = 16):
        super().__init__(display, is_active, return_screen)
        self.item_height = item_height
        self.max_items_shown = self.display.height // item_height
        self.setItems(items)
        
    
    def setItems(self, items):
        self.items = items
        if self.items == None:
            self.items = list()
        self.current_index = 0
        self.first_shown = 0
        self.last_shown = min(len(self.items)-1, self.max_items_shown-1)

    def addItem(self, item):
        self.items.append(item)
        
    def removeLastItem(self):
        self.items.removeAt(-1)
    
    def down(self):
        new_current_index = self.current_index + 1
        if new_current_index >= len(self.items):
            new_current_index = len(self.items) - 1
        if new_current_index != self.current_index:
            self.current_index = new_current_index
            if self.current_index - 1 == self.last_shown:
                self.first_shown += 1
                self.last_shown += 1
            self.draw()
    
    def up(self):
        new_current_index = self.current_index - 1
        if new_current_index < 0:
            new_current_index = 0
        if new_current_index != self.current_index:
            self.current_index = new_current_index
            if self.current_index + 1 == self.first_shown:
                self.first_shown -= 1
                self.last_shown -= 1
            self.draw()
    
    def ok(self):
        if self.items[self.current_index] != None and self.items[self.current_index].screen != None:
            self.items[self.current_index].screen.return_screen = self
        return self.items[self.current_index].screen
    
    def draw(self):
        self.display.fill(0)
        for i in range(self.last_shown - self.first_shown + 1):
            index = i + self.first_shown
            if index == self.current_index:
                self.display.fill_rect(0, i*self.item_height, self.display.width, self.item_height, 1)
                self.display.text(self.items[index].title, 0, i*self.item_height + ((self.item_height - 8) // 2), 0)
            else:
                self.display.text(self.items[index].title, 0, i*self.item_height + ((self.item_height - 8) // 2), 1)
        self.display.show()
            

class MenuItem:
    def __init__(self, title, screen):
        self.title = title
        self.screen = screen

class DefualtText(Screen):
    def __init__(self, display, is_active=False, return_screen=None, text=None, lines=None, line_height=10, line_width=None, max_lines_shown=None):
        super().__init__(display, is_active, return_screen)
        self.lines = lines if lines != None else list()
        
        self.line_width = line_width
        if self.line_width == None:
            self.line_width = self.display.width
        
        if text != None:
            self.appendText(text)

        self.line_height = line_height
        self.max_lines_shown = max_lines_shown
        if self.max_lines_shown == None:
            self.max_lines_shown = self.display.height // line_height
        self.first_shown_line = 0

    def appendText(self, text):
        tmp_lines = text.splitlines()
        chars_per_line = self.line_width // 8
        for line in tmp_lines:
            for start in range(0, len(line), chars_per_line):
                self.lines.append(line[start:start + chars_per_line])
        

    def draw(self):
        self.display.fill(0)
        for i in range(self.max_lines_shown):
            index = self.first_shown_line + i
            if index >= len(self.lines):
                break
            self.display.text(self.lines[index], 0, self.line_height * i, 1)
        self.display.show()
    
    def down(self):
        self.first_shown_line += 1
        if self.first_shown_line + self.max_lines_shown > len(self.lines):
            self.first_shown_line = max(0, len(self.lines) - self.max_lines_shown)
        self.draw()

    def up(self):
        self.first_shown_line -= 1
        if self.first_shown_line < 0:
            self.first_shown_line = 0
        self.draw()

class CustomText(Screen):
    def __init__(self, display, is_active=False, return_screen=None, text=None, lines=None, line_height=14, line_width=None, max_lines_shown=None):
        super().__init__(display, is_active, return_screen)
        self.writer = Writer(self.display, im9x14u, verbose=False)
        self.writer.set_clip(row_clip=True, col_clip=True, wrap=False)
        self.lines = lines if lines != None else list()
        
        self.line_width = line_width
        if self.line_width == None:
            self.line_width = self.display.width
        
        if text != None:
            self.appendText(text)

        self.line_height = line_height
        self.max_lines_shown = max_lines_shown
        if self.max_lines_shown == None:
            self.max_lines_shown = self.display.height // line_height
        self.first_shown_line = 0

    def appendText(self, text):
        tmp_lines = text.splitlines()
        chars_per_line = self.line_width // 9
        for line in tmp_lines:
            for start in range(0, len(line), chars_per_line):
                self.lines.append(line[start:start + chars_per_line])
        

    def draw(self):
        self.display.fill(0)
        Writer.set_textpos(self.display, 0, 0)
        for i in range(self.max_lines_shown):
            index = self.first_shown_line + i
            if index >= len(self.lines):
                break
            self.writer.printstring(self.lines[index] + "\n")
        self.display.show()
    
    def down(self):
        self.first_shown_line += 1
        if self.first_shown_line + self.max_lines_shown > len(self.lines):
            self.first_shown_line = len(self.lines) - self.max_lines_shown
        self.draw()

    def up(self):
        self.first_shown_line -= 1
        if self.first_shown_line < 0:
            self.first_shown_line = 0
        self.draw()

class Lines(Screen):
    def __init__(self, display, is_active=False, return_screen=None):
        super().__init__(display, is_active, return_screen)
        self.current_scene = 0
        self.max_scenes = 7
    
    def activate(self):
        self.current_scene = 0
        self.draw()
        return super().activate()

    def draw(self):
        self.display.fill(0)
        if self.current_scene == 0:
            self.display.hline(10, 10, self.display.width - 20, 1)
            self.display.hline(10, self.display.height - 10, self.display.width - 20, 1)
            self.display.vline(10, 10, self.display.height - 20, 1)
            self.display.vline(self.display.width - 10, 10, self.display.height - 20, 1)
        elif self.current_scene == 1:
            offset = self.display.width - self.display.height
            offset = offset // 2
            size = self.display.height // 2
            self.display.line(offset+1, size, offset + size, 1, 1)
            self.display.line(offset + size, 1, self.display.width - offset-1, size, 1)
            self.display.line(offset + size, self.display.height-1, self.display.width - offset - 1, size, 1)
            self.display.line(offset + 1, size , offset + size, self.display.height-1, 1)
        elif self.current_scene == 2:
            self.display.line(0, 0, self.display.width, self.display.height, 1)
            self.display.line(0, self.display.height, self.display.width, 0, 1)
        elif self.current_scene == 3:
            self.display.fill(1)
            self.display.line(0, 0, self.display.width, self.display.height, 0)
            self.display.line(0, self.display.height, self.display.width, 0, 0)
            self.display.hline(0, self.display.height // 2, self.display.width, 0)
            self.display.vline(self.display.width // 2, 0, self.display.height, 0)
        elif self.current_scene == 4:
            self.display.fill(0)
            step = 10
            x = self.display.width - 1
            y = 0
            while y <= self.display.height - 1:
                self.display.line(0, 0, x, y, 1)
                y += step
            y = self.display.height - 1
            x = 0
            while x <= self.display.width:
                self.display.line(0, 0, x, y, 1)
                x += step
        elif self.current_scene == 5:
            self.display.fill(1)
            step = 10
            x = self.display.width - 1
            y = 0
            while y <= self.display.height - 1:
                self.display.line(0, 0, x, y, 0)
                y += step
            y = self.display.height - 1
            x = 0
            while x <= self.display.width:
                self.display.line(0, 0, x, y, 0)
                x += step
        elif self.current_scene == 6:
            center_w = self.display.width // 2
            center_h = self.display.height // 2
            self.circle(center_w, center_h, (self.display.height // 2)-1, 1)
        self.display.show()
    def circle(self, x0, y0, radius, color):
        # Circle drawing function.  Will draw a single pixel wide circle with
        # center at x0, y0 and the specified radius.
        f = 1 - radius
        ddF_x = 1
        ddF_y = -2 * radius
        x = 0
        y = radius
        self.display.pixel(x0, y0 + radius, color)
        self.display.pixel(x0, y0 - radius, color)
        self.display.pixel(x0 + radius, y0, color)
        self.display.pixel(x0 - radius, y0, color)
        while x < y:
            if f >= 0:
                y -= 1
                ddF_y += 2
                f += ddF_y
            x += 1
            ddF_x += 2
            f += ddF_x
            self.display.pixel(x0 + x, y0 + y, color)
            self.display.pixel(x0 - x, y0 + y, color)
            self.display.pixel(x0 + x, y0 - y, color)
            self.display.pixel(x0 - x, y0 - y, color)
            self.display.pixel(x0 + y, y0 + x, color)
            self.display.pixel(x0 - y, y0 + x, color)
            self.display.pixel(x0 + y, y0 - x, color)
            self.display.pixel(x0 - y, y0 - x, color)
    def ok(self):
        return self.return_screen
    
    def down(self):
        new_current_scene = self.current_scene + 1
        if new_current_scene >= self.max_scenes:
            new_current_scene = self.max_scenes - 1
        if new_current_scene != self.current_scene:
            self.current_scene = new_current_scene
            self.draw()
    
    def up(self):
        new_current_scene = self.current_scene - 1
        if new_current_scene < 0:
            new_current_scene = 0
        if new_current_scene != self.current_scene:
            self.current_scene = new_current_scene
            self.draw()

class Sine(Screen):
    def __init__(self, display, is_active=False, return_screen=None, amplitude=None, freq=360, yoffset=None):
        super().__init__(display, is_active, return_screen)
        self.popup = Popup(display)
        self.phase = 0
        self.amplitude = amplitude if amplitude != None else self.display.height // 2
        self.freq = freq
        self.yoffset = yoffset if yoffset != None else self.display.height // 2
        self.last_update = 0
        self.update_rate = 16
        self.speed = 5
    
    def activate(self):
        self.phase = 0
        self.last_update = 0
        return super().activate()

    def draw(self):
        self.display.fill(0)
        for i in range(self.freq):
            y = int((math.sin((i + self.phase) * 0.017453) * self.amplitude) + self.yoffset)
            x = int((self.display.width / self.freq) * i)
            self.display.pixel(x, y, 1)
        self.display.show()

    def tick(self, now):
        if not self.popup.tick(now) and \
            time.ticks_diff(now, self.last_update) > self.update_rate:
            self.phase += self.speed
            if self.phase == 360:
                self.phase = 0
            self.last_update = now
            self.draw()
    
    def show_update_rate(self):
        self.popup.show(str(self.speed))

    def up(self):
        add = 1
        if self.speed >= 1000:
            add = 100
        elif self.speed >= 100:
            add = 50
        elif self.speed >= 10:
            add = 10
        self.speed += add
        self.show_update_rate()
    def down(self):
        add = 1
        if self.speed >= 1000:
            add = 100
        elif self.speed >= 100:
            add = 50
        elif self.speed >= 10:
            add = 10
        self.speed -= add
        if self.speed < 0:
            self.speed = 0
        self.show_update_rate()

class Cube(Screen):
    def __init__(self, display, is_active=False, return_screen=None):
        super().__init__(display, is_active, return_screen)
        self.reset()
        self.popup = Popup(display)
        self.size = 700
    
    def reset(self):
        d = 3
        self.px = [-d,  d,  d, -d, -d,  d,  d, -d]
        self.py = [-d, -d,  d,  d, -d, -d,  d,  d]
        self.pz = [-d, -d, -d, -d,  d,  d,  d,  d]

        self.p2x = [0,0,0,0,0,0,0,0]
        self.p2y = [0,0,0,0,0,0,0,0]
        self.r = [0,0,0]
        self.last_update = 0
        self.update_rate = 16
    
    def activate(self):
        self.reset()
        return super().activate()
    
    def draw(self):
        self.display.fill(0)
        for i in range(3):
            self.display.line(int(self.p2x[i]),   int(self.p2y[i]),   int(self.p2x[i+1]), int(self.p2y[i+1]), 1)
            self.display.line(int(self.p2x[i+4]), int(self.p2y[i+4]), int(self.p2x[i+5]), int(self.p2y[i+5]), 1)
            self.display.line(int(self.p2x[i]),   int(self.p2y[i]),   int(self.p2x[i+4]), int(self.p2y[i+4]), 1)

        self.display.line(int(self.p2x[3]), int(self.p2y[3]), int(self.p2x[0]), int(self.p2y[0]), 1)
        self.display.line(int(self.p2x[7]), int(self.p2y[7]), int(self.p2x[4]), int(self.p2y[4]), 1)
        self.display.line(int(self.p2x[3]), int(self.p2y[3]), int(self.p2x[7]), int(self.p2y[7]), 1)
        self.display.show()
    
    def update(self):
        self.r[0] = self.r[0] + math.pi / 180.0
        self.r[1] = self.r[1] + math.pi / 180.0
        self.r[2] = self.r[2] + math.pi / 180.0
        if (self.r[0] >= 360.0 * math.pi / 180.0):
            self.r[0] = 0
        if (self.r[1] >= 360.0 * math.pi / 180.0):
            self.r[1] = 0
        if (self.r[2] >= 360.0 * math.pi / 180.0):
            self.r[2] = 0

        for i in range(8):
            px2 = self.px[i]
            py2 = math.cos(self.r[0]) * self.py[i] - math.sin(self.r[0]) * self.pz[i]
            pz2 = math.sin(self.r[0]) * self.py[i] + math.cos(self.r[0]) * self.pz[i]

            px3 = math.cos(self.r[1]) * px2 + math.sin(self.r[1]) * pz2
            py3 = py2
            pz3 = -math.sin(self.r[1]) * px2 + math.cos(self.r[1]) * pz2

            ax = math.cos(self.r[2]) * px3 - math.sin(self.r[2]) * py3
            ay = math.sin(self.r[2]) * px3 + math.cos(self.r[2]) * py3
            az = pz3 - 150

            self.p2x[i] = self.display.width / 2 + ax * self.size / az
            self.p2y[i] = self.display.height / 2 + ay * self.size / az
    
    def tick(self, now):
        if not self.popup.tick(now) and \
            time.ticks_diff(now, self.last_update) > self.update_rate:
            self.update()
            self.last_update = now
            self.draw()
    
    def show_update_rate(self):
        self.popup.show(str(self.update_rate) + "ms")
    
    def down(self):
        self.update_rate -= 10
        if self.update_rate < 0:
            self.update_rate = 0
        self.show_update_rate()
        
    def up(self):
        self.update_rate += 10
        self.show_update_rate()

class Flash(Screen):
    def __init__(self, display, is_active=False, return_screen=None):
        super().__init__(display, is_active, return_screen)
        self.init_values()
        self.popup = Popup(display)

    def init_values(self):
        self.last_update = 0
        self.update_rate = 500
        self.color = 0

    def activate(self):
        self.init_values()
        return super().activate()

    def draw(self):
        self.display.fill(self.color)
        self.display.show()
    
    def tick(self, now):
        if not self.popup.tick(now) \
            and time.ticks_diff(now, self.last_update) > self.update_rate:
            if self.color == 0:
                self.color = 1
            else:
                self.color = 0
            self.last_update = now
            self.draw()
    
    def show_update_rate(self):
        self.popup.show(str(self.update_rate) + "ms")
    
    def down(self):
        self.update_rate -= 50
        if self.update_rate < 0:
            self.update_rate = 0
        self.show_update_rate()

    def up(self):
        self.update_rate += 50
        self.show_update_rate()

class Popup:
    def __init__(self, display, title="", duration=1000):
        self.display = display
        self.title = title
        self.duration = duration
        self.last_update = 0
        self.visible = False
        self.timer_running = False
    
    def show(self, title=None):
        if title != None:
            self.title = title
        self.visible = True
        self.timer_running = False
    
    def draw(self):
        self.display.fill(0)
        self.display.text(self.title, 0, 0)
        self.display.show()
    
    def tick(self, now):
        if self.visible:
            if self.timer_running == False:
                self.timer_running = True
                self.last_update = now
                self.draw()
            elif time.ticks_diff(now, self.last_update) >= self.duration:
                self.visible = False
                self.timer_running = False
        return self.visible

class Contrast(Screen):
    def __init__(self, display, is_active=False, return_screen=None, min=0, max=0xff, default_val=0xff, step=1):
        super().__init__(display, is_active=is_active, return_screen=return_screen)
        self.popup = Popup(self.display)
        self.min = min
        self.max = max
        self.value = default_val
        self.test_pattern_visible = False
        self.step = step
    def show_value(self):
        self.popup.show(title=str(self.value))
    def up(self):
        self.value += self.step
        if self.value > self.max:
            self.value = self.max
        self.display.contrast(self.value)
        self.show_value()
    def down(self):
        self.value -= self.step
        if self.value < self.min:
            self.value = self.min
        self.display.contrast(self.value)
        self.show_value()
    def tick(self, now):
        if self.popup.tick(now):
            self.test_pattern_visible = False
        elif self.test_pattern_visible == False:
            self.display.fill(0)
            start_color = 0
            color = 0
            for x in range(self.display.width):
                color = start_color
                for y in range(self.display.height):
                    self.display.pixel(x, y, color)
                    color = 1 if color == 0 else 0
                start_color = 1 if color == 0 else 0
            self.display.show()
            self.test_pattern_visible = True

class LCDBacklight(Screen):
    def __init__(self, display, pin, default_val=0, off_val=0, is_active=False, return_screen=None,):
        super().__init__(display, is_active=is_active, return_screen=return_screen)
        self.pin = pin
        self.value = default_val
        self.off_val = off_val
        self.on_val = 1 if off_val == 0 else 0
        
        self.up = self.change_value
        self.down = self.change_value
    def draw(self):
        if self.value == self.off_val:
            self.display.fill(0)
            self.display.text("Bklght Off", 0, 0, 1)
        else:
            self.display.fill(1)
            self.display.text("Bklght On", 0, 0, 0)
        self.display.show()
    def change_value(self):
        self.value = self.off_val if self.value == self.on_val else self.on_val
        self.pin.value(self.value)
        self.draw()
class Images(Screen):
    def __init__(self, display, images, is_active=False, return_screen=None):
        super().__init__(display, is_active=is_active, return_screen=return_screen)
        self.images = images
        self.current_image = 0
    def draw(self):
        if self.current_image >= len(self.images):
            self.display.fill(0)
            self.display.show()
            return
        self.display.fill(0)
        self.display.blit(self.images[self.current_image], 0, 0)
        self.display.show()
    def up(self):
        new_current_image = self.current_image - 1
        if new_current_image < 0:
            new_current_image = 0
        if new_current_image != self.current_image:
            self.current_image = new_current_image
            self.draw()
    def down(self):
        new_current_image = self.current_image + 1
        if new_current_image >= len(self.images):
            new_current_image = self.current_image
        if new_current_image != self.current_image:
            self.current_image = new_current_image
            self.draw()
    
def pcd_init():
    spi = SPI(1)
    spi.init(baudrate=2000000, polarity=0, phase=0)
    cs = Pin(8)
    dc = Pin(7)
    rst = Pin(9)
    # backlight on
    lcd_backlight = Pin(3, Pin.OUT, value=0)
    lcd = pcd8544_fb.PCD8544_FB(spi, cs, dc, rst)
    
    return lcd, lcd_backlight


def oled_init():
    i2c = I2C(0, scl=Pin(5), sda=Pin(4))
    display = ssd1306.SSD1306_I2C(128, 64, i2c)
    
    return display

lcd, lcd_backlight = pcd_init()
oled = oled_init()

btn_down = Button(18)
btn_up = Button(19)
btn_ok = Button(20)


default_text = "Ahoj Svete!\nAaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvXxYyZz\n0123456789\n!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
text = "Ahoj Světe!\nAaBbCcČčDdĎďEeĚěÉéFfGgHhIiÍíJjKkLlMmNnŇňOoÓóPpQqRrŘřSsŠšTtŤťUuÚúŮůVvXxYyÝýZzŽž"

contrast_items_lcd = [
    MenuItem(b"LCD", Contrast(lcd, min=0, max=0x7f, default_val=0x3f)),
    MenuItem(b"OLED", DefualtText(lcd)),
    MenuItem(b"Back", None)
    ]
contrast_items_oled = [
    MenuItem(b"LCD", DefualtText(oled)), 
    MenuItem(b"OLED", Contrast(oled, min=0, max=0xff, default_val=0xff, step=10)),
    MenuItem(b"Back", None)
    ]

lcd_images = [
    framebuf.FrameBuffer(
        bytearray(b'\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x80\x40\x40\x40\x80\x80\xC0\xC0\x40\xC0\xA0\xE0\xC0\xE0\xE0\xF0\xF0\xF8\xF8\xF8\xFC\xFC\xFE\xEE\xF4\xF0\xF0\x70\x30\x00\x80\x00\x00\x80\x00\x0C\x9C\x1C\x38\xB8\x38\x38\xB8\xF8\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF8\xF8\xF8\xF8\x88\x20\x8A\x20\x08\x22\x08\x00\x0A\x00\x00\x02\x80\x71\xBA\xDA\xFD\xDD\xED\xDE\xEE\xF7\xFF\xFB\xFD\xFD\xFE\xFF\x7F\x3F\x1F\x9F\x3F\x7F\x6F\x0F\xAF\x1F\xBF\x3E\x3C\x7A\x78\x70\x22\x88\xA0\x2A\x80\x08\x62\xE0\xE0\xF2\xF0\x58\xDA\xF8\xFC\x92\xFE\xFF\xFF\xD3\xFF\xFD\xF3\xE1\xF0\xF9\x7F\xBF\x3F\x8F\x2F\x4F\xAF\x0F\x4F\xA7\x0F\xAF\x87\x2F\x82\x80\x20\xC0\x80\x80\x50\x40\xC4\xD0\xA0\xE8\xE4\xEA\xFF\xFB\xFD\xFF\xFF\xFF\xFF\xFF\xEF\x4F\x27\x53\xA8\x54\x29\x4A\xB5\x82\xAC\xA1\x8A\xB6\x50\x4D\x32\xA4\x4A\xB4\xA9\x4A\x52\xB4\xAA\x45\xA8\xDA\x22\xAC\xD2\x2A\x52\xA8\x52\x4C\xB0\xAD\x43\x5B\xB3\x45\xA8\x5B\xA3\xAB\x55\xA8\x52\x54\xA9\x56\xA8\x45\xBA\xA4\x49\x5A\xA2\x54\xAA\x52\xFE\xFF\xFF\xFE\xFD\xFF\xFF\xFF\xFE\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F\xFF\xFE\xBF\x7F\xBF\xBF\xFF\xDF\xBF\x5F\xDF\x7F\xDF\x7F\xDF\xAF\x7F\xEE\x8E\xF1\x6E\x99\xF7\x6A\xDD\xB2\x6E\xD5\x7A\xD7\xAC\x75\xDB\x6D\xD5\x7A\xD7\xAC\x7B\xE5\xDE\xA9\x77\xDA\xB5\xEE\x59\xB6\xEB\xDD\xB6\x69\xD6\xBF\xE8\x55\xEF\xB9\xD6\xED\xB5\x5B\xAB\xFF\xFD\xF7\xFF\x01\x01\x01\x01\xE1\xC1\x81\x03\x05\x0F\x1D\x2F\x7E\x01\x00\x01\x01\xFF\xFE\x03\x01\x01\x00\xF1\xF0\xF1\x71\xF1\xF1\xB1\xF1\x01\x01\x01\x03\xFE\xFF\x01\x01\x01\x01\xBE\x1B\x0D\x07\x03\x41\xE1\xF1\xF9\x6D\xFF\xFF\x00\x01\x01\x01\xFF\xFF\xEB\x3E\x0D\x03\x01\x41\x71\x70\x41\x01\x03\x0E\x3B\xEF\xFE\xFB\xEE\x7D\xF7\xFF\xFF\xFF\xFF\xFE\xFF\xF0\xF0\xF0\xF0\xFF\xFF\xFF\xFF\xFE\xFC\xF8\xF0\xF0\xF0\xF0\xF0\xF0\xFF\xFF\xF8\xF0\xF0\xF0\xF1\xF1\xF1\xF1\xF1\xF1\xF1\xF1\xF0\xF0\xF0\xF8\xFF\xFF\xF0\xF0\xF0\xF0\xFF\xFF\xFE\xFC\xF8\xF0\xF0\xF1\xF3\xF7\xFF\xFF\xF0\xF0\xF0\xF0\xFF\xF3\xF0\xF0\xF0\xFC\xFC\xFC\xFC\xFC\xFC\xFC\xFC\xF0\xF0\xF0\xF3\xFF\xFF\xFF\xFF\xFF'), 
        84, 48, framebuf.MONO_VLSB
        ),
    framebuf.FrameBuffer(
        bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00|?\x00\x01\x86@\x80\x01\x01\x80\x80\x01\x11\x88\x80\x01\x05\xa0\x80\x00\x83\xc1\x00\x00C\xe3\x00\x00~\xfc\x00\x00L'\x00\x00\x9c\x11\x00\x00\xbf\xfd\x00\x00\xe1\x87\x00\x01\xc1\x83\x80\x02A\x82@\x02A\x82@\x02\xc1\xc2@\x02\xf6>\xc0\x01\xfc=\x80\x01\x18\x18\x80\x01\x88\x10\x80\x00\x8c!\x00\x00\x87\xf1\x00\x00\x7f\xf6\x00\x008\x1c\x00\x00\x0c \x00\x00\x03\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"),
         32, 32, framebuf.MONO_HLSB), 
    framebuf.FrameBuffer(
        bytearray(b'\xE0\x38\xE4\x22\xA2\xE1\xE1\x61\xE1\x21\xA2\xE2\xE4\x38\xE0\x03\x0C\x10\x21\x21\x41\x48\x48\x48\x49\x25\x21\x10\x0C\x03'),
         15, 15, framebuf.MONO_VLSB), 
]
oled_images = [
    framebuf.FrameBuffer(
        bytearray(b'\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x00\x00\x80\x80\x40\x40\x40\x80\x80\xC0\xC0\x40\xC0\xA0\xE0\xC0\xE0\xE0\xF0\xF0\xF8\xF8\xF8\xFC\xFC\xFE\xEE\xF4\xF0\xF0\x70\x30\x00\x80\x00\x00\x80\x00\x0C\x9C\x1C\x38\xB8\x38\x38\xB8\xF8\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF0\xF8\xF8\xF8\xF8\x88\x20\x8A\x20\x08\x22\x08\x00\x0A\x00\x00\x02\x80\x71\xBA\xDA\xFD\xDD\xED\xDE\xEE\xF7\xFF\xFB\xFD\xFD\xFE\xFF\x7F\x3F\x1F\x9F\x3F\x7F\x6F\x0F\xAF\x1F\xBF\x3E\x3C\x7A\x78\x70\x22\x88\xA0\x2A\x80\x08\x62\xE0\xE0\xF2\xF0\x58\xDA\xF8\xFC\x92\xFE\xFF\xFF\xD3\xFF\xFD\xF3\xE1\xF0\xF9\x7F\xBF\x3F\x8F\x2F\x4F\xAF\x0F\x4F\xA7\x0F\xAF\x87\x2F\x82\x80\x20\xC0\x80\x80\x50\x40\xC4\xD0\xA0\xE8\xE4\xEA\xFF\xFB\xFD\xFF\xFF\xFF\xFF\xFF\xEF\x4F\x27\x53\xA8\x54\x29\x4A\xB5\x82\xAC\xA1\x8A\xB6\x50\x4D\x32\xA4\x4A\xB4\xA9\x4A\x52\xB4\xAA\x45\xA8\xDA\x22\xAC\xD2\x2A\x52\xA8\x52\x4C\xB0\xAD\x43\x5B\xB3\x45\xA8\x5B\xA3\xAB\x55\xA8\x52\x54\xA9\x56\xA8\x45\xBA\xA4\x49\x5A\xA2\x54\xAA\x52\xFE\xFF\xFF\xFE\xFD\xFF\xFF\xFF\xFE\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\x7F\xFF\xFE\xBF\x7F\xBF\xBF\xFF\xDF\xBF\x5F\xDF\x7F\xDF\x7F\xDF\xAF\x7F\xEE\x8E\xF1\x6E\x99\xF7\x6A\xDD\xB2\x6E\xD5\x7A\xD7\xAC\x75\xDB\x6D\xD5\x7A\xD7\xAC\x7B\xE5\xDE\xA9\x77\xDA\xB5\xEE\x59\xB6\xEB\xDD\xB6\x69\xD6\xBF\xE8\x55\xEF\xB9\xD6\xED\xB5\x5B\xAB\xFF\xFD\xF7\xFF\x01\x01\x01\x01\xE1\xC1\x81\x03\x05\x0F\x1D\x2F\x7E\x01\x00\x01\x01\xFF\xFE\x03\x01\x01\x00\xF1\xF0\xF1\x71\xF1\xF1\xB1\xF1\x01\x01\x01\x03\xFE\xFF\x01\x01\x01\x01\xBE\x1B\x0D\x07\x03\x41\xE1\xF1\xF9\x6D\xFF\xFF\x00\x01\x01\x01\xFF\xFF\xEB\x3E\x0D\x03\x01\x41\x71\x70\x41\x01\x03\x0E\x3B\xEF\xFE\xFB\xEE\x7D\xF7\xFF\xFF\xFF\xFF\xFE\xFF\xF0\xF0\xF0\xF0\xFF\xFF\xFF\xFF\xFE\xFC\xF8\xF0\xF0\xF0\xF0\xF0\xF0\xFF\xFF\xF8\xF0\xF0\xF0\xF1\xF1\xF1\xF1\xF1\xF1\xF1\xF1\xF0\xF0\xF0\xF8\xFF\xFF\xF0\xF0\xF0\xF0\xFF\xFF\xFE\xFC\xF8\xF0\xF0\xF1\xF3\xF7\xFF\xFF\xF0\xF0\xF0\xF0\xFF\xF3\xF0\xF0\xF0\xFC\xFC\xFC\xFC\xFC\xFC\xFC\xFC\xF0\xF0\xF0\xF3\xFF\xFF\xFF\xFF\xFF'), 
        84, 48, framebuf.MONO_VLSB
        ),
    framebuf.FrameBuffer(
        bytearray(b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00|?\x00\x01\x86@\x80\x01\x01\x80\x80\x01\x11\x88\x80\x01\x05\xa0\x80\x00\x83\xc1\x00\x00C\xe3\x00\x00~\xfc\x00\x00L'\x00\x00\x9c\x11\x00\x00\xbf\xfd\x00\x00\xe1\x87\x00\x01\xc1\x83\x80\x02A\x82@\x02A\x82@\x02\xc1\xc2@\x02\xf6>\xc0\x01\xfc=\x80\x01\x18\x18\x80\x01\x88\x10\x80\x00\x8c!\x00\x00\x87\xf1\x00\x00\x7f\xf6\x00\x008\x1c\x00\x00\x0c \x00\x00\x03\xc0\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"),
         32, 32, framebuf.MONO_HLSB), 
    framebuf.FrameBuffer(
        bytearray(b'\xE0\x38\xE4\x22\xA2\xE1\xE1\x61\xE1\x21\xA2\xE2\xE4\x38\xE0\x03\x0C\x10\x21\x21\x41\x48\x48\x48\x49\x25\x21\x10\x0C\x03'),
         15, 15, framebuf.MONO_VLSB), 
]

items_lcd = [
    MenuItem(b"Def. text", DefualtText(lcd, text=default_text)), 
    MenuItem(b"Def. text2", DefualtText(lcd, text=default_text, line_width=84, max_lines_shown=4)),
    MenuItem(b"Cstm fonts", CustomText(lcd, text=text)),
    MenuItem(b"Cstm fnts2", CustomText(lcd, text=text, line_width=84, max_lines_shown=3)), 
    MenuItem(b"Lines", Lines(lcd)), 
    MenuItem(b"Sine", Sine(lcd)), 
    MenuItem(b"Cube anim", Cube(lcd)), 
    MenuItem(b"Scrn flash", Flash(lcd)), 
    MenuItem(b"Images", Images(lcd, images=lcd_images)), 
    MenuItem(b"Contrast", Menu(lcd, items=contrast_items_lcd)),
    MenuItem(b"LCD bklght", LCDBacklight(lcd, pin=lcd_backlight, default_val=0, off_val=1)), 
    ]
items_oled = [
    MenuItem(b"Default text", DefualtText(oled, text=default_text)), 
    MenuItem(b"Default text2", DefualtText(oled, text=default_text, line_width=84, max_lines_shown=4)), 
    MenuItem(b"Custom fonts", CustomText(oled, text=text)),
    MenuItem(b"Custom fonts2", CustomText(oled, text=text, line_width=84, max_lines_shown=3)), 
    MenuItem(b"Lines", Lines(oled)), 
    MenuItem(b"Sine", Sine(oled)), 
    MenuItem(b"Cube animation", Cube(oled)), 
    MenuItem(b"Screen flash", Flash(oled)), 
    MenuItem(b"Images", Images(oled, images=oled_images)), 
    MenuItem(b"Contrast", Menu(oled, items=contrast_items_oled)), 
    MenuItem(b"LCD backlight", LCDBacklight(oled, pin=lcd_backlight, default_val=0, off_val=1)), 
    ]

menu_lcd = Menu(lcd, items=items_lcd)
menu_oled = Menu(oled, items=items_oled)

contrast_items_lcd[2].screen = menu_lcd
contrast_items_oled[2].screen = menu_oled

screen_lcd = menu_lcd
screen_oled = menu_oled



screen_lcd.activate()
screen_oled.activate()

while True:
    now = time.ticks_ms()
    if btn_ok.isPressed(now):
        new_screen_lcd = screen_lcd.ok()
        if isinstance(new_screen_lcd, Screen) and new_screen_lcd is not screen_lcd:
            screen_lcd.deactivate()
            screen_lcd = new_screen_lcd
            screen_lcd.activate()
        
        new_screen_oled = screen_oled.ok()
        if isinstance(new_screen_oled, Screen) and new_screen_oled is not screen_oled:
            screen_oled.deactivate()
            screen_oled = new_screen_oled
            screen_oled.activate()
    elif btn_up.isPressed(now):
        screen_lcd.up()
        screen_oled.up()
    elif btn_down.isPressed(now):
        screen_lcd.down()
        screen_oled.down()
    
    screen_lcd.tick(now)
    screen_oled.tick(now)
    