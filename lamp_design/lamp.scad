// ============================================
// 灯具设计 - 北欧极简风格吊灯
// 作者: Iris ☁️
// ============================================

// ===== 参数设置 =====
/* [灯罩参数] */
dome_radius = 60;          // 穹顶半径 (mm)
dome_height = 45;          // 穹顶高度
dome_thickness = 2.5;      // 灯罩壁厚
dome_segments = 64;         // 平滑度

/* [光源缝隙] */
slit_height = 8;           // 底部缝隙高度
slit_count = 6;             // 缝隙数量
slit_width = 3;            // 缝隙宽度 (mm)

/* [装饰件] */
top_knob_radius = 8;       // 顶部装饰球半径
top_knob_height = 12;      // 顶部连接柱高度
top_ring_height = 5;       // 顶部环高度

/* [吊装件] */
cord_length = 500;         // 电源线长度 (mm)
cord_radius = 2;            // 电源线半径
canopy_radius = 30;         // 天花板装饰盘半径
canopy_height = 8;          // 天花板装饰盘高度

/* [底座] */
diffuser_radius = 40;      // 底部透光罩半径
diffuser_height = 15;      // 底部透光罩高度

/* [材质颜色] */
lamp_color = [0.95, 0.93, 0.90];  // 暖白色 (灯罩)
metal_color = [0.25, 0.23, 0.22]; // 深色金属 (装饰)
diffuser_color = [1.0, 0.98, 0.95, 0.6]; // 半透明白 (扩散罩)

// ===== 辅助模块 =====

// 圆环模块
module torus(r_major, r_minor) {
    rotate_extrude(convexity = 10)
        translate([r_major, 0, 0])
            circle(r = r_minor);
}

// 顶部装饰组件
module top_assembly() {
    // 天花板装饰盘
    color(metal_color)
    translate([0, 0, cord_length])
        cylinder(r = canopy_radius, h = canopy_height, center = false);
    
    // 装饰盘边缘倒角
    color(metal_color)
    translate([0, 0, cord_length + canopy_height - 2])
        torus(canopy_radius - 2, 2);
    
    // 连接柱
    color(metal_color)
    translate([0, 0, cord_length + canopy_height])
        cylinder(r = 4, h = top_ring_height, center = false);
    
    // 顶部装饰球
    color(metal_color)
    translate([0, 0, cord_length + canopy_height + top_ring_height])
        sphere(r = top_knob_radius, $fn = 32);
    
    // 电源线
    color([0.15, 0.15, 0.15])
    translate([0, 0, 0])
        cylinder(r = cord_radius, h = cord_length, center = false);
}

// 穹顶灯罩
module dome_shade() {
    color(lamp_color) {
        difference() {
            // 外壳 - 抛物面穹顶
            translate([0, 0, dome_height])
                scale([1, 1, dome_height / dome_radius])
                    sphere(r = dome_radius, $fn = dome_segments);
            
            // 挖空内部
            translate([0, 0, dome_height + 1])
                scale([1, 1, dome_height / dome_radius])
                    sphere(r = dome_radius - dome_thickness, $fn = dome_segments);
            
            // 底部开口 (保留边缘)
            translate([-dome_radius - 5, -dome_radius - 5, -5])
                cube([(dome_radius + 5) * 2, (dome_radius + 5) * 2, slit_height + 5]);
        }
    }
}

// 底部缝隙
module slit_cutouts() {
    for (i = [0 : slit_count - 1]) {
        angle = i * 360 / slit_count;
        rotate([0, 0, angle])
            translate([diffuser_radius - slit_width - 2, -slit_width/2, -1])
                cube([20, slit_width, slit_height + 2]);
    }
}

// 底部透光罩
module bottom_diffuser() {
    color(diffuser_color)
    translate([0, 0, -diffuser_height])
        cylinder(r = diffuser_radius, h = diffuser_height, center = false);
}

// 装饰环
module decorative_ring(r, h, y_offset) {
    color(metal_color)
    translate([0, 0, h])
        rotate_extrude(convexity = 10)
            translate([r, y_offset, 0])
                circle(r = 2, $fn = 16);
}

// ===== 主模型 =====
module lamp() {
    // 顶部组件
    top_assembly();
    
    // 装饰环 1 (顶部)
    decorative_ring(dome_radius * 0.4, cord_length + canopy_height + top_ring_height + top_knob_radius * 2 - 2, 0);
    
    // 穹顶灯罩
    translate([0, 0, dome_height + dome_height/2])
        dome_shade();
    
    // 底部缝隙 (从灯罩切出)
    translate([0, 0, dome_height + dome_height/2])
        slit_cutouts();
    
    // 装饰环 2 (中部)
    translate([0, 0, dome_height * 0.3])
        decorative_ring(dome_radius * 0.85, 0, -dome_height * 0.15);
    
    // 底部透光罩
    translate([0, 0, -diffuser_height])
        bottom_diffuser();
}

// 旋转展示
lamp();

// ===== 渲染设置 =====
$fn = dome_segments;
