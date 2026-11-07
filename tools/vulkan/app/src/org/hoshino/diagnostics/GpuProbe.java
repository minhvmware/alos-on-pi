package org.hoshino.diagnostics;
import android.app.Activity;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import android.widget.LinearLayout;
import android.view.Surface;
import android.view.SurfaceView;
import android.view.SurfaceHolder;
public final class GpuProbe extends Activity {
 static { System.loadLibrary("hoshinoprobe"); }
 private static native String probe();
 private static native String present(Surface surface);
 public void onCreate(Bundle state) {
  super.onCreate(state);
  TextView text=new TextView(this); text.setTextSize(18); text.setPadding(32,32,32,32);
  LinearLayout panel=new LinearLayout(this);panel.setOrientation(LinearLayout.VERTICAL);panel.addView(text);
  SurfaceView view=new SurfaceView(this);panel.addView(view,new LinearLayout.LayoutParams(-1,400));setContentView(panel);
  view.getHolder().addCallback(new SurfaceHolder.Callback(){
   public void surfaceCreated(SurfaceHolder holder){new Thread(() -> {
    String report=probe()+"\n"+present(holder.getSurface());Log.i("HoshinoGpuProbe",report);runOnUiThread(() -> text.setText(report));
   },"VulkanSurfaceProbe").start();}
   public void surfaceChanged(SurfaceHolder h,int f,int w,int height){}
   public void surfaceDestroyed(SurfaceHolder h){}
  });
  text.setText("Vulkan GPU test\nRunning…");
 }
}
