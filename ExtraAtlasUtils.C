#include "TLine.h"
#include "TLatex.h"
#include "TMarker.h"
#include "TPave.h"

void myTextVarSize(Double_t x,Double_t y,Color_t color, const char *text, Double_t s) {

  //Double_t tsize=0.05;
  TLatex l; //l.SetTextAlign(12);
  l.SetTextSize(s); 
  l.SetNDC();
  l.SetTextColor(color);
  l.DrawLatex(x,y,text);
}

void myBoxTextColorAlpha(Double_t x, Double_t y,Double_t boxsize,Int_t mcolor,const char *text,Int_t lcolor, Double_t alpha=0)
{

  Double_t tsize=0.06;

  TLatex l; l.SetTextAlign(12); //l.SetTextSize(tsize); 
  l.SetNDC();
  l.DrawLatex(x,y,text);

  Double_t y1=y-0.25*tsize;
  Double_t y2=y+0.25*tsize;
  Double_t x2=x-0.3*tsize;
  Double_t x1=x2-boxsize;

  printf("x1= %f x2= %f y1= %f y2= %f \n",x1,x2,y1,y2);

  TPave *mbox= new TPave(x1,y1,x2,y2,0,"NDC");

  mbox->SetFillColor(mcolor);
  mbox->SetFillStyle(1001);
  if (alpha) mbox->SetFillColorAlpha(mcolor, alpha);
  mbox->Draw();

  TLine mline;
  mline.SetLineWidth(4);
  mline.SetLineColor(lcolor);
  mline.SetLineStyle(1);
  Double_t y_new=(y1+y2)/2.;
  mline.DrawLineNDC(x1,y_new,x2,y_new);

}
