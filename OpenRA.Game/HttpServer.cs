using System;
using System.Collections.Generic;
using System.Net;
using System.Text;
using OpenRA.Mods.Common.Traits;

namespace OpenRA
{
	public class HttpServer
	{
		public static HttpListener Listener;
		public static string Url = "http://localhost:12345/";
		public static int PageViews = 0;
		public static int RequestCount = 0;
		public static string PageData =
			"<!DOCTYPE>" +
			"<html>" +
			"  <head>" +
			"    <title>HttpListener Example</title>" +
			"  </head>" +
			"  <body>" +
			"    <p>Page Views: {0}</p>" +
			"    <form method=\"post\" action=\"shutdown\">" +
			"      <input type=\"submit\" value=\"Shutdown\" {1}>" +
			"    </form>" +
			"  </body>" +
			"</html>";

		public static async void HandleIncomingConnections()
		{
			bool runServer = true;

			// While a user hasn't visited the `shutdown` url, keep on handling requests
			while (runServer)
			{
				// Will wait here until we hear from a connection
				HttpListenerContext ctx = await Listener.GetContextAsync();

				// Peel out the requests and response objects
				HttpListenerRequest req = ctx.Request;
				HttpListenerResponse resp = ctx.Response;

				// Print out some info about the request
				Console.WriteLine(req.Url.ToString());

				World world = Game.OrderManager.World;

				if (world == null)
				{
					continue;
				}

				PlayerResources playerResources = world.LocalPlayer.PlayerActor.Trait<PlayerResources>();

				if (req.Url.AbsolutePath == "/review")
				{
					int n = 0;
					HashSet<string> refineries = new HashSet<string> { "proc", "refinery" };
					foreach (Actor a in world.Actors)
					{
						if (a.Owner == world.LocalPlayer && refineries.Contains(a.Info.Name.ToLower()))
						{
							n++;
						}
					}

					int cash = (int)(Math.Sqrt(n) * double.Parse(req.Headers.Get("multiplier")));
					Console.WriteLine("Giving {0}", cash);
					playerResources.GiveCash(cash);
				}

				// If `shutdown` url requested w/ POST, then shutdown the server after serving the page
				if ((req.HttpMethod == "POST") && (req.Url.AbsolutePath == "/shutdown"))
				{
					Console.WriteLine("Shutdown requested");
					runServer = false;
				}

				// Make sure we don't increment the page views counter if `favicon.ico` is requested
				if (req.Url.AbsolutePath != "/favicon.ico")
					PageViews += 1;

				// Write the response info
				string disableSubmit = !runServer ? "disabled" : "";
				byte[] data = Encoding.UTF8.GetBytes(string.Format(playerResources.Cash.ToString()));
				resp.ContentType = "text/html";
				resp.ContentEncoding = Encoding.UTF8;
				resp.ContentLength64 = data.LongLength;

				// Write out to the response stream (asynchronously), then close it
				await resp.OutputStream.WriteAsync(data, 0, data.Length);
				resp.Close();
			}
		}
	}
}
